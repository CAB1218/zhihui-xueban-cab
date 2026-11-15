"""
智慧学伴 模型健康检查 Celery beat 任务
每 60 秒执行一次，探测各 LLM Provider 的健康状态

流程:
1. 遍历 LLMRouter 所有 provider
2. 对 is_available=True 的 provider 发送轻量探测请求（max_tokens=1）
3. 更新 ModelProvider.avg_latency_ms / success_rate / last_check_time
4. 对 is_available=False 的 provider，若探测成功则恢复
5. 同步健康指标到 Redis Hash: model:health:{provider}
"""
import asyncio
import logging
import time

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.health_check.health_check_task")
def health_check_task() -> dict:
    """模型健康检查任务（Celery beat 每 60s 执行）

    Returns:
        {"checked": int, "available": int, "recovered": int, "failed": int}
    """
    logger.info("[HealthCheck] 开始模型健康检查")

    # 在事件循环中执行异步探测
    return asyncio.run(_async_health_check())


async def _async_health_check() -> dict:
    """异步健康检查逻辑"""
    from app.agents.llm_router import llm_router

    # 确保 router 已初始化
    await llm_router._initialize()

    checked = 0
    available = 0
    recovered = 0
    failed = 0

    for provider_name in llm_router._priority:
        provider = llm_router._providers.get(provider_name)
        if not provider or not provider.is_configured:
            continue

        checked += 1
        was_available = provider.is_available

        try:
            # 发送轻量探测请求（max_tokens=1）
            start_time = time.time()
            result = await _probe_provider(provider)
            latency_ms = int((time.time() - start_time) * 1000)

            # 探测成功
            llm_router._record_success(provider)
            llm_router._update_health_metrics(provider, latency_ms, success=True)

            if not was_available:
                recovered += 1
                logger.info("[HealthCheck] Provider %s 已恢复", provider.provider)
            else:
                available += 1

        except Exception as e:
            # 探测失败
            llm_router._record_failure(provider, str(e))
            llm_router._update_health_metrics(provider, 0, success=False)
            failed += 1
            logger.warning(
                "[HealthCheck] Provider %s 探测失败: %s", provider.provider, str(e)[:200]
            )

        # 同步健康指标到 Redis
        await _sync_health_to_redis(provider)

    logger.info(
        "[HealthCheck] 完成: checked=%d, available=%d, recovered=%d, failed=%d",
        checked, available, recovered, failed,
    )

    return {
        "checked": checked,
        "available": available,
        "recovered": recovered,
        "failed": failed,
    }


async def _probe_provider(provider) -> dict:
    """发送轻量探测请求（max_tokens=1）

    Args:
        provider: ModelProvider 实例

    Returns:
        LLM 响应

    Raises:
        Exception: 探测失败时抛出
    """
    import httpx
    from app.config import settings

    url = f"{provider.api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {provider.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": provider.model_name,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "stream": False,
    }

    timeout = float(settings.LLM_HEALTH_CHECK_TIMEOUT)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def _sync_health_to_redis(provider) -> None:
    """同步健康指标到 Redis Hash: model:health:{provider}

    Hash 字段: avg_latency_ms, success_rate, failure_count, last_check_time, is_available
    """
    try:
        from app.core.redis import get_redis_client

        redis = await get_redis_client()
        key = f"model:health:{provider.provider}"

        await redis.hset(key, mapping={
            "avg_latency_ms": str(round(provider.avg_latency_ms, 1)),
            "success_rate": str(round(provider.success_rate, 4)),
            "failure_count": str(provider.failure_count),
            "last_check_time": str(provider.last_check_time),
            "is_available": "1" if provider.is_available else "0",
        })
    except Exception as e:
        logger.debug("[HealthCheck] Redis 同步失败（不影响主流程）: %s", e)
