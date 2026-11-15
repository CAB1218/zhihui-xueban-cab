"""
智慧学伴 OCR 多 Provider 抽象层
支持阿里云/腾讯云/Mock 三种 OCR 服务，按优先级链降级

设计模式: Strategy + Factory
- BaseOCRProvider: 抽象基类，定义 extract() 接口
- AliyunOCRProvider / TencentOCRProvider / MockOCRProvider: 具体实现
- OCRProviderFactory: 工厂方法，按配置优先级返回可用 provider
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """OCR 提取结果"""

    text: str = ""
    confidence: float = 0.0
    provider: str = "unknown"
    raw_response: Optional[dict] = field(default=None)


class BaseOCRProvider(ABC):
    """OCR 提供者抽象基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称"""
        ...

    @abstractmethod
    async def extract(self, image_url: str) -> OCRResult:
        """从图片 URL 提取文字

        Args:
            image_url: 图片的 MinIO 路径或公网 URL

        Returns:
            OCRResult: 提取结果
        """
        ...


class AliyunOCRProvider(BaseOCRProvider):
    """阿里云 OCR（通用文字识别）

    API: https://ocr-api.cn-hangzhou.aliyuncs.com/api/v1/services/ocr/general
    需配置 ALIYUN_OCR_API_KEY
    """

    @property
    def provider_name(self) -> str:
        return "aliyun"

    async def extract(self, image_url: str) -> OCRResult:
        """调用阿里云 OCR API"""
        url = f"{settings.ALIYUN_OCR_ENDPOINT}/api/v1/services/ocr/general"
        headers = {
            "Authorization": f"Bearer {settings.ALIYUN_OCR_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {"url": image_url}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            # 阿里云 OCR 返回格式: { "content": "...", "prism_wordsInfo": [...] }
            text_parts = []
            for block in data.get("prism_wordsInfo", []):
                word = block.get("word", "")
                if word:
                    text_parts.append(word)

            return OCRResult(
                text="\n".join(text_parts),
                confidence=float(data.get("confidence", 0.9)),
                provider="aliyun",
                raw_response=data,
            )
        except Exception as e:
            logger.error("阿里云 OCR 调用失败: %s", e)
            raise


class TencentOCRProvider(BaseOCRProvider):
    """腾讯云 OCR（通用印刷体识别）

    API: ocr.tencentcloudapi.com
    需配置 TENCENT_OCR_SECRET_ID / TENCENT_OCR_SECRET_KEY
    """

    @property
    def provider_name(self) -> str:
        return "tencent"

    async def extract(self, image_url: str) -> OCRResult:
        """调用腾讯云 OCR API"""
        # 腾讯云需要签名，这里简化实现（生产环境建议使用 tencentcloud-sdk-python）
        url = "https://ocr.tencentcloudapi.com"
        headers = {
            "Content-Type": "application/json",
            "X-TC-Action": "GeneralBasicOCR",
            "X-TC-Region": settings.TENCENT_OCR_REGION,
        }
        payload = {"ImageUrl": image_url}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()

            # 腾讯云返回格式: { "TextDetections": [{ "DetectedText": "..." }] }
            text_parts = []
            for block in data.get("TextDetections", []):
                detected = block.get("DetectedText", "")
                if detected:
                    text_parts.append(detected)

            return OCRResult(
                text="\n".join(text_parts),
                confidence=0.9,
                provider="tencent",
                raw_response=data,
            )
        except Exception as e:
            logger.error("腾讯云 OCR 调用失败: %s", e)
            raise


class MockOCRProvider(BaseOCRProvider):
    """Mock OCR，开发环境使用（无需 API Key）"""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def extract(self, image_url: str) -> OCRResult:
        """返回固定的 Mock 文本"""
        logger.info("[MockOCR] 模拟提取图片: %s", image_url)
        return OCRResult(
            text=(
                "[Mock OCR] 检测到板书内容：函数与极限\n"
                "1. 函数定义：设 x 和 y 是两个变量，D 是给定的数集\n"
                "2. 极限概念：当 x 趋近于 x₀ 时，f(x) 趋近于 A\n"
                "3. 连续性：lim(x→x₀) f(x) = f(x₀)\n"
                "4. 导数定义：f'(x₀) = lim(Δx→0) [f(x₀+Δx) - f(x₀)] / Δx"
            ),
            confidence=0.95,
            provider="mock",
        )


class OCRProviderFactory:
    """OCR Provider 工厂，按优先级链降级

    优先级由 settings.OCR_PROVIDER_PRIORITY 控制（逗号分隔）
    默认: aliyun → tencent → mock
    """

    @classmethod
    def get_provider(cls) -> BaseOCRProvider:
        """按优先级返回第一个可用的 provider"""
        priority_str = settings.OCR_PROVIDER_PRIORITY or "aliyun,tencent,mock"
        chain = [name.strip() for name in priority_str.split(",") if name.strip()]

        for name in chain:
            provider = cls._create_provider(name)
            if provider is not None:
                logger.info("OCR Provider 已选择: %s", name)
                return provider

        # 兜底：返回 Mock
        logger.warning("所有 OCR Provider 不可用，使用 Mock")
        return MockOCRProvider()

    @classmethod
    def _create_provider(cls, name: str) -> Optional[BaseOCRProvider]:
        """创建指定名称的 provider，配置不可用时返回 None"""
        if name == "aliyun":
            if settings.ALIYUN_OCR_API_KEY:
                return AliyunOCRProvider()
        elif name == "tencent":
            if settings.TENCENT_OCR_SECRET_ID and settings.TENCENT_OCR_SECRET_KEY:
                return TencentOCRProvider()
        elif name == "mock":
            return MockOCRProvider()
        return None


# 全局单例
ocr_provider = OCRProviderFactory.get_provider()
