"""
智慧学伴 通用响应/分页/错误码 Schema
"""
from typing import Any, ClassVar, Generic, List, Optional, Tuple, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """统一API响应格式"""

    code: int = Field(default=200, description="状态码")
    data: Optional[T] = Field(default=None, description="响应数据")
    message: str = Field(default="success", description="响应消息")


class PaginationParams(BaseModel):
    """分页参数"""

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页数量")
    total_pages: int = Field(default=0, description="总页数")

    def __init__(self, **data):
        super().__init__(**data)
        if self.total > 0 and self.page_size > 0:
            self.total_pages = (self.total + self.page_size - 1) // self.page_size


class ErrorCode:
    """错误码定义（普通类，非 Pydantic Model）"""

    # 通用错误
    UNKNOWN_ERROR: ClassVar[Tuple[int, str]] = (1000, "未知错误")
    PARAM_ERROR: ClassVar[Tuple[int, str]] = (1001, "参数错误")
    PERMISSION_DENIED: ClassVar[Tuple[int, str]] = (1002, "权限不足")

    # 认证相关
    AUTH_FAILED: ClassVar[Tuple[int, str]] = (2001, "认证失败")
    TOKEN_EXPIRED: ClassVar[Tuple[int, str]] = (2002, "Token已过期")
    TOKEN_INVALID: ClassVar[Tuple[int, str]] = (2003, "Token无效")
    ACCOUNT_DISABLED: ClassVar[Tuple[int, str]] = (2004, "账号已禁用")
    LOGIN_REQUIRED: ClassVar[Tuple[int, str]] = (2005, "请先登录")

    # 用户相关
    USER_NOT_FOUND: ClassVar[Tuple[int, str]] = (3001, "用户不存在")
    EMAIL_EXISTS: ClassVar[Tuple[int, str]] = (3002, "邮箱已注册")
    PASSWORD_ERROR: ClassVar[Tuple[int, str]] = (3003, "密码错误")

    # 资源相关
    RESOURCE_NOT_FOUND: ClassVar[Tuple[int, str]] = (4001, "资源不存在")
    RESOURCE_UPLOAD_FAILED: ClassVar[Tuple[int, str]] = (4002, "资源上传失败")
    RESOURCE_TYPE_ERROR: ClassVar[Tuple[int, str]] = (4003, "资源类型不支持")

    # 场景相关
    SCENE_NOT_FOUND: ClassVar[Tuple[int, str]] = (5001, "场景不存在")
    SCENE_SWITCH_FAILED: ClassVar[Tuple[int, str]] = (5002, "场景切换失败")

    # AI相关
    AI_SERVICE_ERROR: ClassVar[Tuple[int, str]] = (6001, "AI服务异常")
    AI_RATE_LIMIT: ClassVar[Tuple[int, str]] = (6002, "AI请求频率超限")

    # 租户相关
    TENANT_NOT_FOUND: ClassVar[Tuple[int, str]] = (7001, "租户不存在")
    TENANT_EXPIRED: ClassVar[Tuple[int, str]] = (7002, "租户已过期")
