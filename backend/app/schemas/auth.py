"""
AI4Edu 认证 Schema
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """登录请求"""

    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")


class LoginResponse(BaseModel):
    """登录响应"""

    access_token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")
    token_type: str = Field(default="bearer", description="Token类型")
    expires_in: int = Field(..., description="过期时间(秒)")
    user_id: int = Field(..., description="用户ID")
    nickname: str = Field(..., description="昵称")
    role: str = Field(..., description="角色")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    onboarding_completed: bool = Field(default=False, description="是否完成引导")
    major: Optional[str] = Field(default=None, description="专业")


class RegisterRequest(BaseModel):
    """注册请求"""

    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    nickname: str = Field(..., min_length=2, max_length=50, description="昵称")
    role: str = Field(default="student", pattern="^(student|teacher)$", description="角色")
    invite_code: Optional[str] = Field(default=None, description="邀请码（已废弃，不再使用）", deprecated=True)
    school: Optional[str] = Field(default=None, description="学校")
    grade: Optional[str] = Field(default=None, description="年级")
    major: Optional[str] = Field(default=None, min_length=0, max_length=100, description="专业")


class RegisterResponse(BaseModel):
    """注册响应"""

    user_id: int = Field(..., description="用户ID")
    email: str = Field(..., description="邮箱")
    nickname: str = Field(..., description="昵称")
    access_token: str = Field(..., description="Access Token")
    refresh_token: str = Field(..., description="Refresh Token")
    onboarding_completed: bool = Field(default=False, description="是否完成引导")


class RefreshRequest(BaseModel):
    """刷新Token请求"""

    refresh_token: str = Field(..., description="Refresh Token")


class RefreshResponse(BaseModel):
    """刷新Token响应"""

    access_token: str = Field(..., description="新的Access Token")
    refresh_token: str = Field(..., description="新的Refresh Token")
    token_type: str = Field(default="bearer", description="Token类型")
    expires_in: int = Field(..., description="过期时间(秒)")


class UserInfoResponse(BaseModel):
    """用户信息响应"""

    id: int = Field(..., description="用户ID")
    email: str = Field(..., description="邮箱")
    nickname: str = Field(..., description="昵称")
    avatar_url: Optional[str] = Field(default=None, description="头像URL")
    role: str = Field(..., description="角色")
    grade: Optional[str] = Field(default=None, description="年级")
    school: Optional[str] = Field(default=None, description="学校")
    major: Optional[str] = Field(default=None, description="专业")
    default_scene: str = Field(..., description="默认场景")
    locale: str = Field(..., description="语言偏好")
    onboarding_completed: bool = Field(..., description="是否完成引导")
    tenant_id: Optional[int] = Field(default=None, description="租户ID")
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="偏好设置（theme/default_scene 等）")
    created_at: datetime = Field(..., description="注册时间")
