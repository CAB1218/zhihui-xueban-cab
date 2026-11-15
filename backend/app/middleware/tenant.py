"""
智慧学伴 租户识别中间件
从请求头 X-Tenant-ID 或 JWT Token 中提取租户ID，
动态设置数据库 search_path 实现多租户 Schema 隔离
"""
import re
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.security import decode_access_token


class TenantMiddleware(BaseHTTPMiddleware):
    """
    租户识别中间件

    工作流程：
    1. 优先从请求头 X-Tenant-ID 获取租户ID
    2. 若无请求头，从 JWT Token 的 tenant_id 字段获取
    3. 将租户ID注入到 request.state.tenant_id
    4. 公共路径（/health, /docs等）跳过租户检查
    """

    # 不需要租户检查的路径
    PUBLIC_PATHS = {
        "/health",
        "/",
        "/docs",
        "/redoc",
        "/openapi.json",
    }

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件处理逻辑"""

        # 公共路径跳过租户检查
        if request.url.path in self.PUBLIC_PATHS:
            request.state.tenant_id = None
            request.state.tenant_schema = "public"
            return await call_next(request)

        # 登录/注册路径跳过（尚未有Token）
        if request.url.path.endswith(("/login", "/register", "/refresh")):
            request.state.tenant_id = None
            request.state.tenant_schema = "public"
            return await call_next(request)

        tenant_id = None

        # 1. 尝试从请求头获取 X-Tenant-ID
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header:
            try:
                tenant_id = int(tenant_header)
            except ValueError:
                pass

        # 2. 若无请求头，从 JWT Token 获取
        if tenant_id is None:
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = decode_access_token(token)
                if payload:
                    tenant_id = payload.get("tenant_id")

        # 设置租户信息到 request.state
        if tenant_id:
            request.state.tenant_id = tenant_id
            request.state.tenant_schema = f"tenant_{tenant_id}"
        else:
            request.state.tenant_id = None
            request.state.tenant_schema = "public"

        return await call_next(request)
