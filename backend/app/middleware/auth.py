"""
智慧学伴 JWT 认证中间件
校验 Bearer Token 有效性，将用户信息注入 request.state
"""
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import decode_access_token


class AuthMiddleware(BaseHTTPMiddleware):
    """
    JWT 认证中间件

    工作流程：
    1. 对需要认证的路径，从 Authorization 头提取 Bearer Token
    2. 解码验证 Token，提取用户信息
    3. 将 user_id, role, tenant_id 注入 request.state
    4. Token 无效返回 401

    公共路径和登录路径跳过认证检查
    """

    # 不需要认证的路径前缀
    PUBLIC_PATH_PREFIXES = (
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/refresh",
    )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件处理逻辑"""

        # 检查是否为公共路径
        path = request.url.path
        is_public = any(path.startswith(prefix) for prefix in self.PUBLIC_PATH_PREFIXES)
        is_public = is_public or path in ("/", "/health")

        if is_public:
            return await call_next(request)

        # 提取 Bearer Token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={"code": 401, "data": None, "message": "未提供认证凭据"},
            )

        token = auth_header[7:]
        payload = decode_access_token(token)

        if payload is None:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "data": None, "message": "Token无效或已过期"},
            )

        # 注入用户信息到 request.state
        request.state.user_id = payload.get("sub")
        request.state.user_role = payload.get("role")
        request.state.user_tenant_id = payload.get("tenant_id")

        return await call_next(request)
