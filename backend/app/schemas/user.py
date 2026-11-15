"""
智慧学伴 用户 Schema
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """创建用户请求"""

    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: str = Field(..., min_length=2, max_length=50, description="昵称")
    role: str = Field(default="student", description="角色")
    phone: Optional[str] = Field(default=None, description="手机号")
    grade: Optional[str] = Field(default=None, description="年级")
    school: Optional[str] = Field(default=None, description="学校")
    major: Optional[str] = Field(default=None, max_length=100, description="专业")


class UserUpdate(BaseModel):
    """更新用户请求"""

    nickname: Optional[str] = Field(default=None, min_length=2, max_length=50, description="昵称")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    phone: Optional[str] = Field(default=None, description="手机号")
    grade: Optional[str] = Field(default=None, description="年级")
    school: Optional[str] = Field(default=None, description="学校")
    major: Optional[str] = Field(default=None, max_length=100, description="专业")
    bio: Optional[str] = Field(default=None, description="个人简介")


class UserResponse(BaseModel):
    """用户信息响应"""

    id: int = Field(..., description="用户ID")
    email: str = Field(..., description="邮箱")
    nickname: str = Field(..., description="昵称")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    role: str = Field(..., description="角色")
    phone: Optional[str] = Field(default=None, description="手机号")
    grade: Optional[str] = Field(default=None, description="年级")
    school: Optional[str] = Field(default=None, description="学校")
    major: Optional[str] = Field(default=None, description="专业")
    bio: Optional[str] = Field(default=None, description="个人简介")
    default_scene: str = Field(..., description="默认场景")
    locale: str = Field(..., description="语言偏好")
    onboarding_completed: bool = Field(..., description="是否完成引导")
    is_active: bool = Field(..., description="是否启用")
    last_login_at: Optional[datetime] = Field(default=None, description="最后登录时间")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class UserListResponse(BaseModel):
    """用户列表响应"""

    items: list[UserResponse] = Field(default_factory=list, description="用户列表")
    total: int = Field(default=0, description="总数")
    page: int = Field(default=1, description="页码")
    page_size: int = Field(default=20, description="每页数量")


class OnboardingRequest(BaseModel):
    """Onboarding 引导请求"""

    role: str = Field(..., description="选择的角色: student/teacher")
    major: Optional[str] = Field(default=None, max_length=100, description="所在专业")
    interests: List[str] = Field(default_factory=list, min_length=0, description="兴趣学科（完整引导至少3个，跳过时可为空）")
    goals: List[str] = Field(default_factory=list, min_length=0, description="学习目标（跳过时可为空）")
    grade: Optional[str] = Field(default=None, description="年级")
    school: Optional[str] = Field(default=None, description="学校")


class OnboardingResponse(BaseModel):
    """Onboarding 引导响应"""

    user_id: int = Field(..., description="用户ID")
    onboarding_completed: bool = Field(..., description="是否完成引导")
    default_scene: str = Field(..., description="推荐默认场景")
    message: str = Field(default="引导完成", description="提示消息")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class UpdatePreferencesRequest(BaseModel):
    """更新偏好请求"""

    theme: Optional[str] = Field(default=None, pattern="^(light|dark|auto)$", description="主题")
    locale: Optional[str] = Field(default=None, description="语言偏好")
    default_scene: Optional[str] = Field(default=None, description="默认场景")
    sidebar_collapsed: Optional[bool] = Field(default=None, description="侧边栏折叠")
    show_buddy: Optional[bool] = Field(default=None, description="是否显示学伴")
    notification_enabled: Optional[bool] = Field(default=None, description="是否开启通知")
