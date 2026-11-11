"""
AI4Edu 多模型路由器
支持 DeepSeek、腾讯混元、阿里通义千问三个模型提供商
统一 OpenAI 兼容接口调用，自动 fallback 容灾切换
"""
import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.config import settings
from app.agents.scene_config import get_scene_preset

logger = logging.getLogger(__name__)


@dataclass
class ModelProvider:
    """单个模型提供商配置"""

    provider: str  # "deepseek" / "qwen" / "hunyuan"
    api_key: str
    api_base: str
    model_name: str
    is_available: bool = True  # 健康状态
    failure_count: int = 0  # 连续失败计数
    last_error_time: Optional[datetime] = None
    last_error_msg: str = ""
    request_count: int = 0  # 当前窗口请求计数
    window_start: float = field(default_factory=time.time)  # 速率限制窗口起始时间
    # v2 新增：健康指标字段
    avg_latency_ms: float = 0.0       # 平均延迟（毫秒）
    success_rate: float = 1.0         # 成功率（0.0 ~ 1.0）
    last_check_time: float = 0.0      # 最近健康检查时间（timestamp）

    @property
    def is_configured(self) -> bool:
        """是否配置了有效的 API Key"""
        return bool(self.api_key) and self.api_key not in ("", "sk-xxx", "xxx", "sk-your-openai-api-key")


class LLMRouter:
    """多模型路由器 - 全局单例

    负责管理多个模型提供商配置，提供按优先级+健康状态的模型选择，
    以及自动 fallback 的 LLM 调用能力。
    """

    def __init__(self) -> None:
        self._providers: Dict[str, ModelProvider] = {}
        self._priority: List[str] = []
        self._initialized: bool = False
        self._lock = asyncio.Lock()
        # 页面配置（llm_provider_configs 表）的覆盖值，优先于 backend/.env
        self._overrides: Dict[str, Dict[str, str]] = {}
        # .env 基线，页面配置在此基础上覆盖
        self._base_config: Dict[str, Dict[str, str]] = {}
        # 上次从数据库对齐配置的时间（多 worker 场景做 TTL 轮询）
        self._overrides_checked_at: float = 0.0

    async def _initialize(self) -> None:
        """从 settings 加载所有 Provider 配置（懒加载，线程安全）"""
        if self._initialized:
            return
        async with self._lock:
            if self._initialized:
                return

            # .env 里的基线配置，页面配置在此基础上覆盖
            self._base_config = {
                "deepseek": {
                    "api_key": settings.DEEPSEEK_API_KEY,
                    "api_base": settings.DEEPSEEK_API_BASE,
                    "model_name": settings.DEEPSEEK_MODEL,
                },
                "qwen": {
                    "api_key": settings.QWEN_API_KEY,
                    "api_base": settings.QWEN_API_BASE,
                    "model_name": settings.QWEN_MODEL,
                },
                "hunyuan": {
                    "api_key": settings.HUNYUAN_API_KEY,
                    "api_base": settings.HUNYUAN_API_BASE,
                    "model_name": settings.HUNYUAN_MODEL,
                },
            }

            # 构建 Provider 配置（基线 + 页面覆盖）
            providers_config = {}
            for name in self._base_config:
                fields = self._effective_fields(name)
                providers_config[name] = ModelProvider(
                    provider=name,
                    api_key=fields["api_key"],
                    api_base=fields["api_base"],
                    model_name=fields["model_name"],
                )

            self._providers = providers_config

            # 解析优先级
            priority_str = settings.LLM_MODEL_PRIORITY or "deepseek,qwen,hunyuan"
            self._priority = [p.strip() for p in priority_str.split(",") if p.strip()]

            # 确保所有已配置的 provider 都在优先级列表中
            for provider_name in providers_config:
                if provider_name not in self._priority:
                    self._priority.append(provider_name)

            self._initialized = True
            logger.info(
                "LLMRouter 初始化完成，优先级: %s，已配置: %s",
                self._priority,
                [p for p, v in self._providers.items() if v.is_configured],
            )

    def _effective_fields(self, name: str) -> Dict[str, str]:
        """基线（.env）+ 页面配置 → 当前生效的字段"""
        base = (self._base_config or {}).get(name, {})
        override = self._overrides.get(name, {})
        return {
            "api_key": override.get("api_key") or base.get("api_key", "") or "",
            "api_base": override.get("api_base") or base.get("api_base", "") or "",
            "model_name": override.get("model_name") or base.get("model_name", "") or "",
        }

    def _apply_fields(self) -> None:
        """把生效字段刷到 Provider 上（Key 变了要重置熔断状态）"""
        for name, provider in self._providers.items():
            fields = self._effective_fields(name)
            key_changed = provider.api_key != fields["api_key"]
            provider.api_key = fields["api_key"]
            provider.api_base = fields["api_base"]
            provider.model_name = fields["model_name"]
            if key_changed:
                provider.is_available = True
                provider.failure_count = 0
                provider.last_error_msg = ""

    async def apply_overrides(self, overrides: Dict[str, Dict[str, str]]) -> None:
        """应用页面配置（AI 对话 → 模型配置）并立即生效

        覆盖值来自 llm_provider_configs 表，优先级高于 backend/.env。
        传入的 api_key/api_base/model_name 只覆盖出现的键，
        因此可以只改模型名而保留原有 Key。
        """
        await self._initialize()
        self._overrides = overrides or {}
        self._apply_fields()
        self._overrides_checked_at = time.time()

        logger.info(
            "LLMRouter 已应用页面配置: %s",
            [p for p, v in self._providers.items() if v.is_configured],
        )

    async def refresh_overrides(self, ttl: float = 5.0) -> None:
        """多 worker 下让页面保存的配置扩散到所有进程

        uvicorn 起了 4 个 worker，每个进程各有一份内存配置；
        保存接口只更新命中的那个 worker，其余 worker 通过 TTL 轮询数据库对齐。
        """
        now = time.time()
        if now - self._overrides_checked_at < ttl:
            return
        self._overrides_checked_at = now
        try:
            from app.database import async_session_factory
            from app.services import llm_config_service

            async with async_session_factory() as session:
                overrides = await llm_config_service.load_overrides(session)
            if overrides != self._overrides:
                await self.apply_overrides(overrides)
        except Exception as e:  # noqa: BLE001 — 刷新失败不应影响对话主流程
            logger.warning("刷新模型配置失败: %s", e)

    def get_provider(self, name: str) -> Optional[ModelProvider]:
        """按名称取 Provider 配置（不存在返回 None）"""
        return self._providers.get(name)

    async def reload(self) -> None:
        """丢弃已加载的配置，下次调用时按 settings + overrides 重新初始化"""
        async with self._lock:
            self._initialized = False
            self._providers = {}
            self._priority = []

    async def get_model(
        self,
        scene_type: Optional[str] = None,
        preferred: Optional[str] = None,
    ) -> Optional[ModelProvider]:
        """获取可用模型

        选择顺序：preferred → 场景偏好 → 优先级链遍历

        Args:
            scene_type: 场景类型，用于查询场景偏好模型
            preferred: 用户/调用方指定的首选 provider

        Returns:
            可用的 ModelProvider，若全部不可用则返回 None
        """
        await self._initialize()
        await self.refresh_overrides()

        # 构建尝试顺序
        candidates: List[str] = []

        # 1. 首选
        if preferred:
            candidates.append(preferred)

        # 2. 场景偏好
        if scene_type:
            preset = get_scene_preset(scene_type)
            if preset and preset.preferred_model not in candidates:
                candidates.append(preset.preferred_model)

        # 3. 优先级链
        for p in self._priority:
            if p not in candidates:
                candidates.append(p)

        # 遍历候选，返回第一个可用的
        for provider_name in candidates:
            provider = self._providers.get(provider_name)
            if provider and not self._should_skip(provider):
                return provider

        # 所有候选都不可用，尝试返回任意一个已配置的
        for provider_name in self._priority:
            provider = self._providers.get(provider_name)
            if provider and provider.is_configured:
                return provider

        return None

    async def call_llm(
        self,
        messages: List[Dict[str, str]],
        scene_type: Optional[str] = None,
        preferred: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        tenant_id: Optional[int] = None,
        session_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """调用 LLM，自动 fallback

        v2 改造: 调用前检查配额，调用后记录用量

        Args:
            messages: 消息列表（含系统提示词）
            scene_type: 场景类型
            preferred: 首选 provider
            temperature: 生成温度
            max_tokens: 最大生成 token 数
            tenant_id: 租户ID（用于配额检查）
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            包含 content, model, usage, fallback_info 的字典。
            若所有 Provider 不可用，返回降级标记。
        """
        await self._initialize()
        await self.refresh_overrides()

        # v2 新增：配额检查
        if tenant_id:
            try:
                from app.services.quota_manager import quota_manager

                allowed, reason = await quota_manager.check_quota(
                    tenant_id, estimated_tokens=1000
                )
                if not allowed:
                    logger.warning("租户 %s 配额超限: %s", tenant_id, reason)
                    await quota_manager.record_usage(
                        tenant_id, 0, provider="none", model_name="none",
                        session_id=session_id, user_id=user_id,
                        status="quota_exceeded",
                    )
                    return {
                        "content": "⚠️ 今日 AI 额度已用完，请明天再试或联系管理员。",
                        "model": "quota-exceeded",
                        "usage": {},
                        "degraded": True,
                        "fallback_info": None,
                        "quota_exceeded": True,
                    }
            except Exception as e:
                logger.warning("配额检查异常（放行）: %s", e)

        # 获取候选 provider 链
        candidates = self._get_candidate_chain(scene_type, preferred)

        if not candidates:
            # 没有任何已配置的 Provider
            logger.warning("没有已配置的 LLM Provider，降级为 demo 模式")
            return {
                "content": "",
                "model": "demo-rule-engine",
                "usage": {},
                "degraded": True,
                "fallback_info": None,
            }

        fallback_from: Optional[str] = None
        fallback_reason: Optional[str] = None

        start_time = time.time()

        for i, provider in enumerate(candidates):
            if self._should_skip(provider):
                continue

            # 尝试调用（含重试）
            attempts = 0
            max_attempts = settings.LLM_MAX_FAILURES

            while attempts < max_attempts:
                try:
                    result = await self._call_provider(
                        provider, messages, temperature, max_tokens
                    )
                    self._record_success(provider)

                    latency_ms = int((time.time() - start_time) * 1000)

                    # v2 新增：更新健康指标
                    self._update_health_metrics(provider, latency_ms, success=True)

                    # 如果发生了 fallback，记录信息
                    fallback_info = None
                    if fallback_from:
                        fallback_info = {
                            "from": fallback_from,
                            "to": provider.provider,
                            "reason": fallback_reason or "unknown",
                        }

                    # v2 新增：记录用量
                    if tenant_id:
                        try:
                            from app.services.quota_manager import quota_manager

                            usage = result.get("usage", {})
                            actual_tokens = usage.get("total_tokens", 0) or self._estimate_tokens(
                                messages, result.get("content", "")
                            )
                            await quota_manager.record_usage(
                                tenant_id, actual_tokens,
                                provider=provider.provider,
                                model_name=provider.model_name,
                                session_id=session_id,
                                user_id=user_id,
                                input_tokens=usage.get("prompt_tokens", 0),
                                output_tokens=usage.get("completion_tokens", 0),
                                latency_ms=latency_ms,
                                status="success",
                            )
                        except Exception as quota_err:
                            logger.warning("用量记录失败: %s", quota_err)

                    return {
                        "content": result["content"],
                        "model": result["model"],
                        "usage": result["usage"],
                        "degraded": False,
                        "fallback_info": fallback_info,
                    }
                except Exception as e:
                    attempts += 1
                    error_msg = str(e)
                    self._record_failure(provider, error_msg)

                    # v2 新增：更新健康指标
                    self._update_health_metrics(provider, 0, success=False)

                    logger.warning(
                        "Provider %s 调用失败 (第%d次): %s",
                        provider.provider,
                        attempts,
                        error_msg[:200],
                    )

                    if attempts >= max_attempts:
                        # 标记不可用，切换到下一个
                        provider.is_available = False
                        fallback_from = provider.provider
                        fallback_reason = self._classify_error(error_msg)
                        logger.info(
                            "Provider %s 连续失败 %d 次，切换到备选模型",
                            provider.provider,
                            attempts,
                        )
                        break
                    # 否则重试同一 Provider

        # 所有 Provider 都不可用
        logger.error("所有 LLM Provider 不可用，降级为 demo 模式")
        return {
            "content": "",
            "model": "demo-rule-engine",
            "usage": {},
            "degraded": True,
            "fallback_info": None,
        }

    async def call_llm_stream(
        self,
        messages: List[Dict[str, str]],
        scene_type: Optional[str] = None,
        preferred: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        """流式调用 LLM，自动 fallback

        Args:
            messages: 消息列表
            scene_type: 场景类型
            preferred: 首选 provider
            temperature: 生成温度
            max_tokens: 最大生成 token 数

        Yields:
            每个输出 token 片段
        """
        await self._initialize()
        await self.refresh_overrides()

        candidates = self._get_candidate_chain(scene_type, preferred)

        if not candidates:
            logger.warning("没有已配置的 LLM Provider，流式降级为 demo 模式")
            return

        for provider in candidates:
            if self._should_skip(provider):
                continue

            try:
                has_content = False
                async for chunk in self._call_provider_stream(
                    provider, messages, temperature, max_tokens
                ):
                    has_content = True
                    yield chunk

                self._record_success(provider)
                if has_content:
                    return  # 成功，退出

            except Exception as e:
                self._record_failure(provider, str(e))
                logger.warning(
                    "Provider %s 流式调用失败: %s，尝试切换备选",
                    provider.provider,
                    str(e)[:200],
                )
                provider.is_available = False
                continue

        # 所有 Provider 不可用，降级提示
        yield "抱歉，AI 服务暂时不可用，请稍后重试。"

    async def health_check(self) -> List[Dict[str, Any]]:
        """检查所有模型可用性

        Returns:
            每个 Provider 的健康状态列表
        """
        await self._initialize()
        await self.refresh_overrides()

        results: List[Dict[str, Any]] = []
        for i, provider_name in enumerate(self._priority):
            provider = self._providers.get(provider_name)
            if not provider:
                continue

            if not provider.is_configured:
                status_str = "not_configured"
            elif not provider.is_available:
                status_str = "unavailable"
            else:
                status_str = "available"

            results.append({
                "provider": provider.provider,
                "model": provider.model_name,
                "status": status_str,
                "is_default": i == 0,
                "is_configured": provider.is_configured,
            })

        return results

    def has_any_configured(self) -> bool:
        """是否有至少一个 Provider 配置了有效 API Key

        Returns:
            True 如果至少有一个已配置的 Provider
        """
        # 同步初始化检查（首次调用时 _initialize 可能未执行）
        if not self._initialized:
            # 同步检查 settings 中的 key
            return any(
                key and key not in ("", "sk-xxx", "xxx", "sk-your-openai-api-key")
                for key in [
                    settings.DEEPSEEK_API_KEY,
                    settings.QWEN_API_KEY,
                    settings.HUNYUAN_API_KEY,
                    settings.OPENAI_API_KEY,
                ]
            )
        return any(p.is_configured for p in self._providers.values())

    def _get_candidate_chain(
        self,
        scene_type: Optional[str],
        preferred: Optional[str],
    ) -> List[ModelProvider]:
        """构建候选 Provider 链"""
        candidates_order: List[str] = []

        # 首选
        if preferred:
            candidates_order.append(preferred)

        # 场景偏好
        if scene_type:
            preset = get_scene_preset(scene_type)
            if preset and preset.preferred_model not in candidates_order:
                candidates_order.append(preset.preferred_model)

        # 优先级链
        for p in self._priority:
            if p not in candidates_order:
                candidates_order.append(p)

        # 如果多模型未启用，加入 OpenAI 配置作为 fallback
        if not settings.LLM_MULTI_MODEL_ENABLED and settings.OPENAI_API_KEY:
            openai_provider = ModelProvider(
                provider="openai",
                api_key=settings.OPENAI_API_KEY,
                api_base=settings.OPENAI_API_BASE,
                model_name=settings.OPENAI_MODEL,
            )
            self._providers["openai"] = openai_provider
            if "openai" not in candidates_order:
                candidates_order.append("openai")

        return [self._providers[name] for name in candidates_order if name in self._providers]

    def _should_skip(self, provider: ModelProvider) -> bool:
        """判断是否应跳过该 Provider

        Args:
            provider: Provider 实例

        Returns:
            True 如果应该跳过（未配置/不可用/速率超限）
        """
        # 未配置有效 API Key
        if not provider.is_configured:
            return True

        # 标记为不可用
        if not provider.is_available:
            return True

        # 速率限制检查
        if settings.LLM_RATE_LIMIT_PER_MINUTE > 0:
            now = time.time()
            # 如果窗口超过 60 秒，重置计数
            if now - provider.window_start > 60:
                provider.request_count = 0
                provider.window_start = now

            if provider.request_count >= settings.LLM_RATE_LIMIT_PER_MINUTE:
                logger.warning("Provider %s 触发速率限制", provider.provider)
                return True

        return False

    async def _call_provider(
        self,
        provider: ModelProvider,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Dict[str, Any]:
        """调用单个 Provider 的 OpenAI 兼容接口

        Args:
            provider: Provider 实例
            messages: 消息列表
            temperature: 生成温度
            max_tokens: 最大 token 数

        Returns:
            {content, model, usage}

        Raises:
            Exception: 调用失败时抛出
        """
        provider.request_count += 1

        url = f"{provider.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider.model_name,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return {
            "content": content,
            "model": data.get("model", provider.model_name),
            "usage": {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            },
        }

    async def _call_provider_stream(
        self,
        provider: ModelProvider,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[str, None]:
        """流式调用单个 Provider

        Args:
            provider: Provider 实例
            messages: 消息列表
            temperature: 生成温度
            max_tokens: 最大 token 数

        Yields:
            每个输出 token 片段
        """
        provider.request_count += 1

        url = f"{provider.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider.model_name,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue

    def _record_failure(self, provider: ModelProvider, error: str) -> None:
        """记录失败，累加 failure_count"""
        provider.failure_count += 1
        provider.last_error_time = datetime.utcnow()
        provider.last_error_msg = error[:500]

        # 如果失败次数超过阈值，标记为不可用
        if provider.failure_count >= settings.LLM_MAX_FAILURES:
            provider.is_available = False
            logger.warning(
                "Provider %s 标记为不可用（连续失败 %d 次）",
                provider.provider,
                provider.failure_count,
            )

    def _record_success(self, provider: ModelProvider) -> None:
        """记录成功，重置 failure_count"""
        if provider.failure_count > 0:
            logger.info("Provider %s 恢复正常", provider.provider)
        provider.failure_count = 0
        provider.is_available = True
        provider.last_error_msg = ""

    def _classify_error(self, error_msg: str) -> str:
        """分类错误原因

        Args:
            error_msg: 错误消息

        Returns:
            错误类别: rate_limit/timeout/server_error/auth_error/network_error/unknown
        """
        error_lower = error_msg.lower()
        if "429" in error_lower or "rate" in error_lower:
            return "rate_limit"
        if "timeout" in error_lower or "timed out" in error_lower:
            return "timeout"
        if "401" in error_lower or "403" in error_lower or "auth" in error_lower:
            return "auth_error"
        if "500" in error_lower or "502" in error_lower or "503" in error_lower:
            return "server_error"
        if "connection" in error_lower or "network" in error_lower:
            return "network_error"
        return "unknown"

    # ============ v2 新增方法 ============

    def _update_health_metrics(
        self, provider: ModelProvider, latency_ms: int, success: bool
    ) -> None:
        """更新 Provider 健康指标（调用成功/失败后触发）

        使用滑动平均更新 avg_latency_ms 和 success_rate

        Args:
            provider: Provider 实例
            latency_ms: 本次调用延迟
            success: 是否成功
        """
        # 更新延迟（指数移动平均，alpha=0.3）
        if success and latency_ms > 0:
            if provider.avg_latency_ms == 0:
                provider.avg_latency_ms = float(latency_ms)
            else:
                provider.avg_latency_ms = 0.7 * provider.avg_latency_ms + 0.3 * float(latency_ms)

        # 更新成功率（指数移动平均）
        success_val = 1.0 if success else 0.0
        provider.success_rate = 0.9 * provider.success_rate + 0.1 * success_val

        # 更新最近检查时间
        provider.last_check_time = time.time()

    def _weighted_select(self, providers: List[ModelProvider]) -> ModelProvider:
        """按 success_rate 加权随机选择

        Args:
            providers: 可用 provider 列表

        Returns:
            选中的 provider
        """
        import random

        weights = [max(p.success_rate, 0.01) for p in providers]
        total = sum(weights)
        if total == 0:
            return providers[0]

        # 加权随机
        r = random.uniform(0, total)
        cumulative = 0.0
        for provider, weight in zip(providers, weights):
            cumulative += weight
            if r <= cumulative:
                return provider

        return providers[-1]

    def _estimate_tokens(self, messages: List[Dict[str, str]], result: str) -> int:
        """粗略估算 token 数（中文 ~1.5 token/字，英文 ~0.75 token/word）

        Args:
            messages: 消息列表
            result: LLM 回复内容

        Returns:
            估算的 token 总数
        """
        input_text = " ".join(m.get("content", "") for m in messages)
        input_tokens = int(len(input_text) * 1.5)
        output_tokens = int(len(result) * 1.5)
        return input_tokens + output_tokens

    def get_balancer_status(self) -> List[Dict[str, Any]]:
        """返回所有 provider 的健康状态摘要

        Returns:
            [{"provider": "deepseek", "model_name": "deepseek-chat",
              "is_available": True, "avg_latency_ms": 1200,
              "success_rate": 0.98, "failure_count": 0, "last_check_time": ...}]
        """
        status_list: List[Dict[str, Any]] = []
        for provider_name in self._priority:
            provider = self._providers.get(provider_name)
            if not provider:
                continue

            status_list.append({
                "provider": provider.provider,
                "model_name": provider.model_name,
                "is_available": provider.is_available,
                "is_configured": provider.is_configured,
                "avg_latency_ms": round(provider.avg_latency_ms, 1),
                "success_rate": round(provider.success_rate, 4),
                "failure_count": provider.failure_count,
                "last_check_time": provider.last_check_time,
            })

        return status_list


# 全局单例
llm_router = LLMRouter()
