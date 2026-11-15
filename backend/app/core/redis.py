"""
智慧学伴 Redis 连接管理
提供 Redis 客户端单例，支持异步操作
"""
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

# 全局 Redis 客户端单例
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """
    获取 Redis 异步客户端单例

    Returns:
        aioredis.Redis: Redis 异步客户端

    Raises:
        ConnectionError: Redis 连接失败
    """
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    _redis_client = aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=50,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )

    # 验证连接
    try:
        await _redis_client.ping()
    except Exception as e:
        _redis_client = None
        raise ConnectionError(f"Redis 连接失败: {e}") from e

    return _redis_client


async def close_redis() -> None:
    """关闭 Redis 连接池"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
