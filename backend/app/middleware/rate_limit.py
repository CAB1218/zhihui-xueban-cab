"""
智慧学伴 限流中间件
基于 Redis 的滑动窗口限流，不同路径不同限制策略
"""
import time
from typing import Callable, Dict, List, Optional, Tuple

from fastapi import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import settings


# ============ 限流规则配置 ============

class RateLimitRule:
    """
    限流规则

    Attributes:
        path_prefix: 路径前缀匹配
        max_requests: 窗口期内最大请求数
        window_seconds: 滑动窗口大小（秒）
    """

    def __init__(
        self,
        path_prefix: str,
        max_requests: int,
        window_seconds: int = 60,
    ) -> None:
        self.path_prefix = path_prefix
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def matches(self, path: str) -> bool:
        """检查路径是否匹配此规则"""
        return path.startswith(self.path_prefix)


# 默认限流规则
DEFAULT_RULES: List[RateLimitRule] = [
    RateLimitRule("/api/v1/auth/", max_requests=30, window_seconds=60),
    RateLimitRule("/api/v1/agents/", max_requests=20, window_seconds=60),
]


# 默认全局限制
DEFAULT_MAX_REQUESTS: int = 60
DEFAULT_WINDOW_SECONDS: int = 60


class RedisSlidingWindowCounter:
    """
    基于 Redis 的滑动窗口计数器

    使用 Redis Sorted Set 实现滑动窗口限流：
    - 每个请求记录时间戳为 score
    - 窗口外的记录自动清理
    - 通过 ZCARD 获取窗口内请求数

    如果 Redis 不可用，降级为内存计数器
    """

    def __init__(self) -> None:
        self._redis = None
        self._memory_store: Dict[str, List[float]] = {}
        self._redis_available: bool = False

    async def _get_redis(self):
        """获取 Redis 连接"""
        if self._redis is not None:
            return self._redis

        try:
            from app.core.redis import get_redis_client
            self._redis = await get_redis_client()
            self._redis_available = True
            return self._redis
        except (ImportError, Exception):
            self._redis_available = False
            return None

    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
    ) -> Tuple[bool, int, int]:
        """
        检查是否超过限流阈值

        Args:
            key: 限流键（如 rate_limit:127.0.0.1:/api/v1/auth/login）
            max_requests: 窗口期内最大请求数
            window_seconds: 窗口大小（秒）

        Returns:
            Tuple[allowed, remaining, retry_after]:
                - allowed: 是否允许请求
                - remaining: 剩余可用请求数
                - retry_after: 需等待秒数（限流时有效）
        """
        now = time.time()
        window_start = now - window_seconds

        redis = await self._get_redis()

        if redis and self._redis_available:
            return await self._check_with_redis(
                redis, key, max_requests, window_seconds, now, window_start
            )
        else:
            return self._check_with_memory(
                key, max_requests, window_seconds, now, window_start
            )

    async def _check_with_redis(
        self,
        redis,
        key: str,
        max_requests: int,
        window_seconds: int,
        now: float,
        window_start: float,
    ) -> Tuple[bool, int, int]:
        """
        使用 Redis Sorted Set 实现滑动窗口

        Args:
            redis: Redis 客户端
            key: 限流键
            max_requests: 最大请求数
            window_seconds: 窗口秒数
            now: 当前时间戳
            window_start: 窗口起始时间戳

        Returns:
            Tuple[allowed, remaining, retry_after]
        """
        try:
            pipe = redis.pipeline()

            # 1. 移除窗口外的旧记录
            pipe.zremrangebyscore(key, 0, window_start)

            # 2. 添加当前请求
            pipe.zadd(key, {str(now): now})

            # 3. 获取窗口内请求数
            pipe.zcard(key)

            # 4. 设置键过期时间
            pipe.expire(key, window_seconds)

            results = await pipe.execute()
            current_count = results[2]

            remaining = max(0, max_requests - current_count)

            if current_count <= max_requests:
                return (True, remaining, 0)
            else:
                # 获取窗口中最早的请求时间，计算重试等待时间
                earliest = await redis.zrange(key, 0, 0, withscores=True)
                retry_after = 1
                if earliest:
                    retry_after = int(earliest[0][1] + window_seconds - now) + 1
                return (False, 0, max(1, retry_after))
        except Exception:
            # Redis 异常降级为放行
            return (True, max_requests, 0)

    def _check_with_memory(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        now: float,
        window_start: float,
    ) -> Tuple[bool, int, int]:
        """
        使用内存实现滑动窗口（Redis 不可用时的降级方案）

        Args:
            key: 限流键
            max_requests: 最大请求数
            window_seconds: 窗口秒数
            now: 当前时间戳
            window_start: 窗口起始时间戳

        Returns:
            Tuple[allowed, remaining, retry_after]
        """
        if key not in self._memory_store:
            self._memory_store[key] = []

        # 清理窗口外记录
        self._memory_store[key] = [
            t for t in self._memory_store[key] if t > window_start
        ]

        # 添加当前请求
        self._memory_store[key].append(now)
        current_count = len(self._memory_store[key])
        remaining = max(0, max_requests - current_count)

        if current_count <= max_requests:
            return (True, remaining, 0)
        else:
            # 移除刚添加的记录
            self._memory_store[key].pop()
            earliest = self._memory_store[key][0] if self._memory_store[key] else now
            retry_after = int(earliest + window_seconds - now) + 1
            return (False, 0, max(1, retry_after))


# 全局计数器实例
_counter = RedisSlidingWindowCounter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    基于 Redis 滑动窗口的限流中间件

    限流策略：
    - /api/v1/auth/*  → 5次/分钟（防止暴力破解）
    - /api/v1/agents/* → 20次/分钟（AI调用成本控制）
    - 其他接口       → 60次/分钟（正常使用）

    限流维度：客户端IP + 路径前缀

    被限流时返回429状态码，响应包含：
    - X-RateLimit-Limit: 窗口期内最大请求数
    - X-RateLimit-Remaining: 剩余可用请求数
    - X-RateLimit-Reset: 窗口重置时间
    - Retry-After: 需等待秒数
    """

    def __init__(self, app, rules: Optional[List[RateLimitRule]] = None):
        """
        初始化限流中间件

        Args:
            app: ASGI应用
            rules: 自定义限流规则列表
        """
        super().__init__(app)
        self.rules = rules or DEFAULT_RULES

    def _get_client_id(self, request: Request) -> str:
        """
        获取客户端标识

        优先使用 X-Forwarded-For 中的真实IP，否则使用连接IP

        Args:
            request: 请求对象

        Returns:
            str: 客户端标识
        """
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _match_rule(self, path: str) -> Tuple[int, int]:
        """
        匹配路径对应的限流规则

        Args:
            path: 请求路径

        Returns:
            Tuple[max_requests, window_seconds]
        """
        for rule in self.rules:
            if rule.matches(path):
                return (rule.max_requests, rule.window_seconds)
        return (DEFAULT_MAX_REQUESTS, DEFAULT_WINDOW_SECONDS)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        执行限流检查

        Args:
            request: 请求对象
            call_next: 下一个中间件/处理器

        Returns:
            Response: 响应对象（429或正常响应）
        """
        path = request.url.path

        # 仅对API路径限流
        if not path.startswith("/api/"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        max_requests, window_seconds = self._match_rule(path)

        # 构建限流键
        # 使用路径前缀而非完整路径，避免为每个具体路径创建独立窗口
        path_prefix = self._get_path_prefix(path)
        rate_limit_key = f"rate_limit:{client_id}:{path_prefix}"

        # 检查限流
        allowed, remaining, retry_after = await _counter.check_rate_limit(
            key=rate_limit_key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        if not allowed:
            return self._create_rate_limit_response(
                max_requests=max_requests,
                remaining=0,
                retry_after=retry_after,
                path=path,
            )

        # 执行请求
        response = await call_next(request)

        # 添加限流响应头
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window_seconds)

        return response

    def _get_path_prefix(self, path: str) -> str:
        """
        获取路径前缀用于限流分组

        /api/v1/auth/login → /api/v1/auth/
        /api/v1/agents/chat → /api/v1/agents/
        /api/v1/notes/123 → /api/v1/notes/

        Args:
            path: 原始路径

        Returns:
            str: 路径前缀
        """
        parts = path.strip("/").split("/")
        if len(parts) >= 3:
            # /api/v1/xxx → /api/v1/xxx/
            return "/" + "/".join(parts[:3]) + "/"
        return path

    def _create_rate_limit_response(
        self,
        max_requests: int,
        remaining: int,
        retry_after: int,
        path: str,
    ) -> JSONResponse:
        """
        创建429限流响应

        Args:
            max_requests: 窗口最大请求数
            remaining: 剩余请求数
            retry_after: 重试等待秒数
            path: 请求路径

        Returns:
            JSONResponse: 429响应
        """
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "code": 429,
                "message": "请求过于频繁，请稍后再试",
                "data": {
                    "retry_after": retry_after,
                    "limit": max_requests,
                    "remaining": remaining,
                    "path": path,
                },
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) + retry_after),
            },
        )
