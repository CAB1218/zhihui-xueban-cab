"""
AI4Edu 认证 API
提供登录、注册、Token刷新、当前用户信息等端点
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    RefreshRequest,
    RefreshResponse,
    UserInfoResponse,
)
from app.schemas.common import APIResponse
from app.database import get_db
from app.services.auth_service import AuthService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.post("/login", response_model=APIResponse[LoginResponse], summary="用户登录")
async def login(
    request: LoginRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[LoginResponse]:
    """
    用户登录

    - 验证邮箱/密码
    - 生成 Access Token 和 Refresh Token
    - 返回用户基本信息（含 onboarding 状态）
    """
    client_ip = http_request.client.host if http_request.client else None
    auth_service = AuthService(db)
    result = await auth_service.authenticate(request, client_ip)
    return APIResponse(data=result)


@router.post("/register", response_model=APIResponse[RegisterResponse], summary="用户注册")
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[RegisterResponse]:
    """
    用户注册

    - 校验邮箱唯一性
    - 创建用户记录（onboarding_completed=False）
    - 生成初始 Token
    - 教师角色需要邀请码
    """
    auth_service = AuthService(db)
    result = await auth_service.register(request)
    return APIResponse(data=result)


@router.post("/refresh", response_model=APIResponse[RefreshResponse], summary="刷新Token")
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[RefreshResponse]:
    """
    刷新 Access Token

    - 验证 Refresh Token 有效性
    - 生成新的 Access Token
    - 检查用户是否仍然有效
    """
    auth_service = AuthService(db)
    result = await auth_service.refresh_access_token(request)
    return APIResponse(data=result)


@router.get("/me", response_model=APIResponse[UserInfoResponse], summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> APIResponse[UserInfoResponse]:
    """
    获取当前登录用户信息

    - 从JWT Token中解析用户ID
    - 返回用户完整信息（含偏好设置，便于「偏好设置」页跨设备回填）
    """
    prefs = None
    if current_user.preferences:
        try:
            prefs = json.loads(current_user.preferences)
        except (ValueError, TypeError):
            prefs = None

    return APIResponse(data=UserInfoResponse(
        id=current_user.id,
        email=current_user.email,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        role=current_user.role,
        grade=current_user.grade,
        school=current_user.school,
        major=current_user.major,
        default_scene=current_user.default_scene,
        locale=current_user.locale,
        onboarding_completed=current_user.onboarding_completed,
        tenant_id=current_user.tenant_id,
        preferences=prefs,
        created_at=current_user.created_at,
    ))


@router.post("/logout", response_model=APIResponse[None], summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_user),
) -> APIResponse[None]:
    """
    用户登出

    - 将当前 Token 加入黑名单（Redis 实现）
    - 清除客户端 Token
    """
    # TODO: 将 Token 加入 Redis 黑名单
    return APIResponse(message="登出成功")
