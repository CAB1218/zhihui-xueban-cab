"""
智慧学伴 ASR 多 Provider 抽象层
支持阿里云/腾讯云/Mock 三种语音识别服务，按优先级链降级

设计模式: Strategy + Factory（与 OCR 层结构一致）
- BaseASRProvider: 抽象基类，定义 transcribe() 接口
- AliyunASRProvider / TencentASRProvider / MockASRProvider: 具体实现
- ASRProviderFactory: 工厂方法
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ASRResult:
    """ASR 语音识别结果"""

    transcript: str = ""
    segments: List[dict] = field(default_factory=list)
    provider: str = "unknown"
    duration_seconds: float = 0.0


class BaseASRProvider(ABC):
    """ASR 语音识别提供者抽象基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名称"""
        ...

    @abstractmethod
    async def transcribe(self, audio_url: str) -> ASRResult:
        """从音频 URL 转录文字

        Args:
            audio_url: 音频/视频的 MinIO 路径或公网 URL

        Returns:
            ASRResult: 转录结果（含分段信息）
        """
        ...


class AliyunASRProvider(BaseASRProvider):
    """阿里云 ASR（录音文件识别）

    异步模式：提交任务 → 轮询结果
    需配置 ALIYUN_ASR_APP_KEY
    """

    @property
    def provider_name(self) -> str:
        return "aliyun"

    async def transcribe(self, audio_url: str) -> ASRResult:
        """调用阿里云 ASR API（提交 + 轮询）"""
        submit_url = f"{settings.ALIYUN_ASR_ENDPOINT}/api/v1/file_trans/submit"
        headers = {
            "Authorization": f"Bearer {settings.ALIYUN_ASR_APP_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "file_url": audio_url,
            "config": {"language_code": "zh-CN"},
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 提交任务
                resp = await client.post(submit_url, headers=headers, json=payload)
                resp.raise_for_status()
                task_data = resp.json()
                task_id = task_data.get("TaskId")

                if not task_id:
                    raise RuntimeError("阿里云 ASR 提交任务失败：未返回 TaskId")

                # 轮询结果（最多等待 5 分钟）
                import asyncio
                query_url = f"{settings.ALIYUN_ASR_ENDPOINT}/api/v1/file_trans/query"
                for _ in range(60):
                    await asyncio.sleep(5)
                    query_resp = await client.get(
                        query_url, headers=headers, params={"TaskId": task_id}
                    )
                    query_resp.raise_for_status()
                    result = query_resp.json()
                    status_code = result.get("StatusCode", -1)

                    if status_code == 21050000:  # 成功
                        sentences = result.get("Result", {}).get("Sentences", [])
                        segments = [
                            {
                                "start": s.get("BeginTime", 0) / 1000.0,
                                "end": s.get("EndTime", 0) / 1000.0,
                                "text": s.get("Text", ""),
                            }
                            for s in sentences
                        ]
                        full_text = "".join(s["text"] for s in segments)
                        duration = segments[-1]["end"] if segments else 0.0

                        return ASRResult(
                            transcript=full_text,
                            segments=segments,
                            provider="aliyun",
                            duration_seconds=duration,
                        )
                    elif status_code != 21050000 and status_code != -1:
                        raise RuntimeError(f"阿里云 ASR 任务失败: {result}")

            raise RuntimeError("阿里云 ASR 轮询超时")
        except Exception as e:
            logger.error("阿里云 ASR 调用失败: %s", e)
            raise


class TencentASRProvider(BaseASRProvider):
    """腾讯云 ASR（录音文件识别）

    API: asr.tencentcloudapi.com
    需配置 TENCENT_ASR_SECRET_ID / TENCENT_ASR_SECRET_KEY
    """

    @property
    def provider_name(self) -> str:
        return "tencent"

    async def transcribe(self, audio_url: str) -> ASRResult:
        """调用腾讯云 ASR API"""
        url = "https://asr.tencentcloudapi.com"
        headers = {
            "Content-Type": "application/json",
            "X-TC-Action": "CreateRecTask",
            "X-TC-Region": settings.TENCENT_ASR_REGION,
        }
        payload = {
            "EngineModelType": "8k_zh",
            "Url": audio_url,
            "ChannelNum": 1,
            "ResTextFormat": 3,  # 包含时间戳
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()

                task_id = data.get("Data", {}).get("TaskId")
                if not task_id:
                    raise RuntimeError("腾讯云 ASR 提交失败")

                # 轮询（简化实现）
                import asyncio
                headers["X-TC-Action"] = "DescribeTaskStatus"
                for _ in range(60):
                    await asyncio.sleep(5)
                    query_resp = await client.post(
                        url, headers=headers, json={"TaskId": task_id}
                    )
                    query_resp.raise_for_status()
                    result = query_resp.json()
                    status = result.get("Data", {}).get("StatusStr", "")

                    if status == "success":
                        text = result.get("Data", {}).get("ResultText", "")
                        return ASRResult(
                            transcript=text,
                            segments=[],
                            provider="tencent",
                            duration_seconds=0.0,
                        )
                    elif status == "failed":
                        raise RuntimeError("腾讯云 ASR 转录失败")

            raise RuntimeError("腾讯云 ASR 轮询超时")
        except Exception as e:
            logger.error("腾讯云 ASR 调用失败: %s", e)
            raise


class MockASRProvider(BaseASRProvider):
    """Mock ASR，开发环境使用（无需 API Key）"""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def transcribe(self, audio_url: str) -> ASRResult:
        """返回固定的 Mock 转录文本"""
        logger.info("[MockASR] 模拟转录音频: %s", audio_url)
        return ASRResult(
            transcript=(
                "[Mock ASR] 今天我们来学习函数与极限。"
                "首先，什么是函数？函数是一种特殊的映射关系。"
                "接下来我们看极限的概念。"
                "极限是微积分的基础，描述了函数值趋近的趋势。"
                "最后，我们来讨论连续性的定义。"
            ),
            segments=[
                {"start": 0.0, "end": 5.2, "text": "今天我们来学习函数与极限。"},
                {"start": 5.2, "end": 12.8, "text": "首先，什么是函数？函数是一种特殊的映射关系。"},
                {"start": 12.8, "end": 18.5, "text": "接下来我们看极限的概念。"},
                {"start": 18.5, "end": 25.3, "text": "极限是微积分的基础，描述了函数值趋近的趋势。"},
                {"start": 25.3, "end": 30.0, "text": "最后，我们来讨论连续性的定义。"},
            ],
            provider="mock",
            duration_seconds=30.0,
        )


class ASRProviderFactory:
    """ASR Provider 工厂，按优先级链降级"""

    @classmethod
    def get_provider(cls) -> BaseASRProvider:
        """按优先级返回第一个可用的 provider"""
        priority_str = settings.OCR_PROVIDER_PRIORITY or "aliyun,tencent,mock"
        chain = [name.strip() for name in priority_str.split(",") if name.strip()]

        for name in chain:
            provider = cls._create_provider(name)
            if provider is not None:
                logger.info("ASR Provider 已选择: %s", name)
                return provider

        logger.warning("所有 ASR Provider 不可用，使用 Mock")
        return MockASRProvider()

    @classmethod
    def _create_provider(cls, name: str) -> Optional[BaseASRProvider]:
        """创建指定名称的 provider"""
        if name == "aliyun":
            if settings.ALIYUN_ASR_APP_KEY:
                return AliyunASRProvider()
        elif name == "tencent":
            if settings.TENCENT_ASR_SECRET_ID and settings.TENCENT_ASR_SECRET_KEY:
                return TencentASRProvider()
        elif name == "mock":
            return MockASRProvider()
        return None


# 全局单例
asr_provider = ASRProviderFactory.get_provider()
