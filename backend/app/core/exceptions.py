"""
智慧学伴 自定义异常与全局异常处理器
统一错误响应格式: {"code": int, "data": null, "message": str}
"""
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    """应用基础异常"""

    def __init__(
        self,
        code: int = 500,
        message: str = "服务器内部错误",
        data: Any = None,
    ):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


class NotFoundException(AppException):
    """资源未找到异常"""

    def __init__(self, message: str = "资源未找到", data: Any = None):
        super().__init__(code=404, message=message, data=data)


class PermissionDeniedException(AppException):
    """权限不足异常"""

    def __init__(self, message: str = "权限不足", data: Any = None):
        super().__init__(code=403, message=message, data=data)


class ValidationException(AppException):
    """数据校验异常"""

    def __init__(self, message: str = "数据校验失败", data: Any = None):
        super().__init__(code=422, message=message, data=data)


class UnauthorizedException(AppException):
    """未认证异常"""

    def __init__(self, message: str = "未认证或认证已过期", data: Any = None):
        super().__init__(code=401, message=message, data=data)


class RateLimitException(AppException):
    """请求频率限制异常"""

    def __init__(self, message: str = "请求过于频繁，请稍后再试", data: Any = None):
        super().__init__(code=429, message=message, data=data)


class TenantNotFoundException(AppException):
    """租户未找到异常"""

    def __init__(self, message: str = "租户不存在", data: Any = None):
        super().__init__(code=400, message=message, data=data)


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """
    全局异常处理器
    将 AppException 转换为统一格式的 JSON 响应

    Args:
        request: 请求对象
        exc: 应用异常

    Returns:
        JSONResponse: 统一格式的错误响应
    """
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "data": exc.data,
            "message": exc.message,
        },
    )
