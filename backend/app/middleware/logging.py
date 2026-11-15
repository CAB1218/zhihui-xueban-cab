"""
智慧学伴 请求日志中间件
使用 structlog 输出结构化 JSON 日志 + 审计日志
"""
import time
import uuid
from typing import Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()
audit_logger = structlog.get_logger("audit")

# 需要审计日志的路径前缀
AUDIT_PATH_PREFIXES = (
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/logout",
    "/api/v1/users/",
    "/api/v1/permissions/",
    "/api/v1/scenes/switch",
)

# 不记录请求日志的路径（健康检查等）
SKIP_LOG_PATHS = {"/health", "/metrics", "/docs", "/redoc", "/openapi.json"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件

    记录内容：
    - 请求ID（X-Request-ID）
    - 请求方法、路径、查询参数
    - 用户ID（如有）
    - 响应状态码
    - 请求耗时（ms）
    - 租户ID（如有）

    审计日志（针对敏感操作）：
    - 登录/登出/注册
    - 用户管理操作
    - 权限变更
    - 场景切换
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件处理逻辑"""
        path = request.url.path

        # 跳过不需要日志的路径
        if path in SKIP_LOG_PATHS:
            return await call_next(request)

        # 生成请求ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # 记录请求开始时间
        start_time = time.perf_counter()

        # 提取基本信息
        method = request.method
        query = str(request.query_params) or None
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        client_ip = request.client.host if request.client else None

        # 普通请求日志
        if not any(path.startswith(prefix) for prefix in AUDIT_PATH_PREFIXES):
            logger.info(
                "request_started",
                request_id=request_id,
                method=method,
                path=path,
                query=query,
                user_id=user_id,
                tenant_id=tenant_id,
                client_ip=client_ip,
            )

        # 执行后续处理
        response: Response = await call_next(request)

        # 计算耗时
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 普通请求完成日志
        logger.info(
            "request_completed",
            request_id=request_id,
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=user_id,
            tenant_id=tenant_id,
        )

        # 审计日志（敏感操作）
        if any(path.startswith(prefix) for prefix in AUDIT_PATH_PREFIXES):
            audit_logger.info(
                "audit_event",
                request_id=request_id,
                method=method,
                path=path,
                query=query,
                status_code=response.status_code,
                user_id=user_id,
                tenant_id=tenant_id,
                client_ip=client_ip,
                duration_ms=duration_ms,
                event_type=self._classify_audit_event(path, method),
            )

        # 在响应头中附加请求ID
        response.headers["X-Request-ID"] = request_id

        return response

    @staticmethod
    def _classify_audit_event(path: str, method: str) -> str:
        """分类审计事件类型"""
        if "/auth/login" in path:
            return "auth.login"
        if "/auth/register" in path:
            return "auth.register"
        if "/auth/logout" in path:
            return "auth.logout"
        if "/auth/refresh" in path:
            return "auth.refresh"
        if "/scenes/switch" in path:
            return "scene.switch"
        if "/permissions" in path:
            return "permission.manage"
        if method == "DELETE" and "/users/" in path:
            return "user.delete"
        if method in ("POST", "PUT") and "/users/" in path:
            return "user.manage"
        if "/users/" in path and "onboarding" in path:
            return "user.onboarding"
        return "api.access"
