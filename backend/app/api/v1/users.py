"""
智慧学伴 用户 API
提供用户 CRUD、Onboarding、偏好设置等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    OnboardingRequest,
    OnboardingResponse,
    ChangePasswordRequest,
    UpdatePreferencesRequest,
)
from app.schemas.common import APIResponse, PaginationParams
from app.database import get_db
from app.services.user_service import UserService
from app.dependencies import get_current_user, require_role
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=APIResponse[UserListResponse], summary="获取用户列表")
async def list_users(
    pagination: PaginationParams = Depends(),
    role: Optional[str] = Query(None, description="按角色筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "super_admin"])),
) -> APIResponse[UserListResponse]:
    """获取用户列表，支持分页、角色筛选和搜索"""
    user_service = UserService(db)
    result = await user_service.list_users(
        page=pagination.page,
        page_size=pagination.page_size,
        role=role,
        search=search,
    )
    return APIResponse(data=UserListResponse(**result))


@router.get("/{user_id}", response_model=APIResponse[UserResponse], summary="获取用户详情")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[UserResponse]:
    """根据ID获取用户详情"""
    user_service = UserService(db)
    result = await user_service.get_user(user_id)
    return APIResponse(data=result)


@router.put("/{user_id}", response_model=APIResponse[UserResponse], summary="更新用户信息")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    """更新用户信息（仅本人或管理员可操作）"""
    # 权限检查：只能更新自己，或管理员可以更新他人
    if current_user.id != user_id and current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="无权修改他人信息")

    user_service = UserService(db)
    result = await user_service.update_user(user_id, data)
    return APIResponse(data=result)


@router.delete("/{user_id}", response_model=APIResponse[None], summary="删除用户")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["super_admin"])),
) -> APIResponse[None]:
    """软删除用户"""
    user_service = UserService(db)
    await user_service.delete_user(user_id)
    return APIResponse(message="用户已删除")


@router.put("/{user_id}/password", response_model=APIResponse[None], summary="修改密码")
async def change_password(
    user_id: int,
    request: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[None]:
    """修改用户密码（仅本人可操作）"""
    if current_user.id != user_id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权修改他人密码")

    user_service = UserService(db)
    await user_service.change_password(user_id, request.old_password, request.new_password)
    return APIResponse(message="密码修改成功")


@router.put("/{user_id}/preferences", response_model=APIResponse[UserResponse], summary="更新用户偏好")
async def update_preferences(
    user_id: int,
    request: UpdatePreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[UserResponse]:
    """更新用户偏好设置（主题、语言、默认场景等）"""
    if current_user.id != user_id and current_user.role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="无权修改他人偏好")

    # 转换为字典，移除 None 值
    preferences = request.model_dump(exclude_none=True)
    user_service = UserService(db)
    result = await user_service.update_preferences(user_id, preferences)
    return APIResponse(data=result)


@router.post("/{user_id}/onboarding", response_model=APIResponse[OnboardingResponse], summary="完成用户引导")
async def complete_onboarding(
    user_id: int,
    request: OnboardingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[OnboardingResponse]:
    """
    完成用户 Onboarding 引导

    - 设置用户角色
    - 记录兴趣和目标
    - 推荐默认场景
    - 标记引导完成
    """
    if current_user.id != user_id and current_user.role != "super_admin":
        raise HTTPException(status_code=403, detail="无权操作")

    user_service = UserService(db)
    result = await user_service.complete_onboarding(user_id, request)
    return APIResponse(data=OnboardingResponse(**result))
