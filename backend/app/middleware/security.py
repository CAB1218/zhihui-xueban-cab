"""
智慧学伴 安全中间件
XSS 防护 + SQL 注入检测 + CSRF Token 校验
"""
import re
import html
from typing import Callable, Set

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

import structlog

logger = structlog.get_logger()

# SQL 注入可疑模式（常见关键字 + 特殊字符组合）
SQL_INJECTION_PATTERNS = [
    re.compile(r"(?i)(\b(union\s+select)\b)"),
    re.compile(r"(?i)(\b(insert\s+into)\b)"),
    re.compile(r"(?i)(\b(delete\s+from)\b)"),
    re.compile(r"(?i)(\b(drop\s+table)\b)"),
    re.compile(r"(?i)(\b(update\s+\w+\s+set)\b)"),
    re.compile(r"(?i)(\b(or\s+1\s*=\s*1\b)"),
    re.compile(r"(?i)(\b(and\s+1\s*=\s*1\b)"),
    re.compile(r"(?i)(--\s*$)"),
    re.compile(r"(?i)(;\s*(drop|delete|update|insert|alter)\b)"),
    re.compile(r"'\s*(or|and)\s+'"),
    re.compile(r"(?i)(\bexec\s*\()"),
    re.compile(r"(?i)(\bxp_cmdshell\b)"),
    re.compile(r"(?i)(\bwaitfor\s+delay\b)"),
    re.compile(r"(?i)(\bbenchmark\s*\()"),
    re.compile(r"(?i)(\bsleep\s*\()"),
]

# XSS 可疑模式
XSS_PATTERNS = [
    re.compile(r"<\s*script", re.IGNORECASE),
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"on(error|load|click|mouseover|focus|blur)\s*=", re.IGNORECASE),
    re.compile(r"<\s*iframe", re.IGNORECASE),
    re.compile(r"<\s*object", re.IGNORECASE),
    re.compile(r"<\s*embed", re.IGNORECASE),
    re.compile(r"expression\s*\(", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
]

# 不需要 CSRF 校验的路径前缀（登录注册等）
CSRF_WHITELIST: Set[str] = {
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/docs",
    "/redoc",
    "/openapi.json",
}

# 不做注入检测的路径前缀
INJECTION_SKIP_PREFIXES = ("/docs", "/redoc", "/openapi.json", "/static")


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    安全中间件

    职责：
    1. XSS 防护 - 检测并拦截请求中的 XSS 载荷
    2. SQL 注入检测 - 检测查询参数和请求体中的 SQL 注入特征
    3. CSRF Token 校验 - 对写操作验证 X-CSRF-Token 头
    4. 安全响应头 - 注入 X-Content-Type-Options, X-Frame-Options 等
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # ---- 1. 注入检测（跳过文档路径） ----
        if not any(path.startswith(p) for p in INJECTION_SKIP_PREFIXES):
            # 检查查询参数
            for key, value in request.query_params.items():
                if self._contains_sql_injection(value):
                    logger.warning("sql_injection_detected", path=path, param=key, value=value[:100])
                    return JSONResponse(
                        status_code=400,
                        content={"code": 400, "data": None, "message": "请求参数包含非法字符"},
                    )
                if self._contains_xss(value):
                    logger.warning("xss_detected", path=path, param=key, value=value[:100])
                    return JSONResponse(
                        status_code=400,
                        content={"code": 400, "data": None, "message": "请求参数包含非法内容"},
                    )

            # 检查请求体（仅 JSON 请求）
            if request.method in ("POST", "PUT", "PATCH") and "application/json" in (request.headers.get("content-type") or ""):
                body = await self._safe_read_body(request)
                if body:
                    injection_field = self._scan_dict_for_injection(body)
                    if injection_field:
                        logger.warning("injection_in_body", path=path, field=injection_field)
                        return JSONResponse(
                            status_code=400,
                            content={"code": 400, "data": None, "message": "请求内容包含非法字符"},
                        )

        # ---- 2. CSRF 校验 ----
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            if not any(path.startswith(w) for w in CSRF_WHITELIST):
                csrf_token = request.headers.get("X-CSRF-Token")
                if not csrf_token:
                    # 如果有 Authorization 头，视为 API 调用，放行（双重提交 Cookie 策略）
                    auth_header = request.headers.get("Authorization")
                    if not auth_header or not auth_header.startswith("Bearer "):
                        logger.warning("csrf_token_missing", path=path, method=request.method)
                        return JSONResponse(
                            status_code=403,
                            content={"code": 403, "data": None, "message": "缺少 CSRF Token"},
                        )

        # ---- 3. 执行后续处理 ----
        response = await call_next(request)

        # ---- 4. 安全响应头 ----
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:;"
        )
        # 如果是 API 请求，设置 CSRF Token 给前端
        if path.startswith("/api/"):
            csrf_token = request.headers.get("X-CSRF-Token") or self._generate_csrf_token()
            response.headers["X-CSRF-Token"] = csrf_token

        return response

    # ============ SQL 注入检测 ============

    @staticmethod
    def _contains_sql_injection(value: str) -> bool:
        """检查字符串是否包含 SQL 注入特征"""
        if not value or len(value) < 3:
            return False
        return any(pattern.search(value) for pattern in SQL_INJECTION_PATTERNS)

    # ============ XSS 检测 ============

    @staticmethod
    def _contains_xss(value: str) -> bool:
        """检查字符串是否包含 XSS 载荷"""
        if not value:
            return False
        return any(pattern.search(value) for pattern in XSS_PATTERNS)

    # ============ 请求体扫描 ============

    @staticmethod
    async def _safe_read_body(request: Request) -> dict | None:
        """安全读取 JSON 请求体，失败返回 None"""
        try:
            return await request.json()
        except Exception:
            return None

    def _scan_dict_for_injection(self, data: dict, prefix: str = "") -> str | None:
        """
        递归扫描字典值是否包含注入内容
        返回触发检测的字段路径，安全则返回 None
        """
        for key, value in data.items():
            field_path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str):
                if self._contains_sql_injection(value):
                    return field_path
                if self._contains_xss(value):
                    return field_path
            elif isinstance(value, dict):
                result = self._scan_dict_for_injection(value, field_path)
                if result:
                    return result
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    item_path = f"{field_path}[{idx}]"
                    if isinstance(item, str):
                        if self._contains_sql_injection(item) or self._contains_xss(item):
                            return item_path
                    elif isinstance(item, dict):
                        result = self._scan_dict_for_injection(item, item_path)
                        if result:
                            return result
        return None

    # ============ CSRF Token 生成 ============

    @staticmethod
    def _generate_csrf_token() -> str:
        """生成 CSRF Token"""
        import secrets
        return secrets.token_hex(32)


def sanitize_input(value: str) -> str:
    """
    清理用户输入，防止 XSS

    Args:
        value: 原始输入

    Returns:
        str: 清理后的安全字符串
    """
    if not value:
        return value
    # HTML 转义
    sanitized = html.escape(value, quote=True)
    return sanitized


def sanitize_dict(data: dict) -> dict:
    """
    递归清理字典中所有字符串值

    Args:
        data: 原始字典

    Returns:
        dict: 清理后的字典
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = sanitize_input(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_input(item) if isinstance(item, str)
                else sanitize_dict(item) if isinstance(item, dict)
                else item
                for item in value
            ]
        else:
            result[key] = value
    return result
