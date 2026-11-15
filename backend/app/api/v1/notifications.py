"""
智慧学伴 通知 API
提供通知列表、已读标记、推送配置等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginationParams
from app.services.notification_service import NotificationService

router = APIRouter()


class NotificationSettingsUpdate(BaseModel):
    """通知设置更新"""

    system_enabled: Optional[bool] = None
    course_enabled: Optional[bool] = None
    assignment_enabled: Optional[bool] = None
    social_enabled: Optional[bool] = None
    ai_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None


@router.get("/", summary="获取通知列表")
async def list_notifications(
    pagination: PaginationParams = Depends(),
    notification_type: Optional[str] = Query(None, description="通知类型筛选"),
    unread_only: bool = Query(False, description="仅显示未读"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取当前用户的通知列表"""
    service = NotificationService(db)
    result = await service.list_notifications(
        user_id=current_user.id,
        pagination=pagination,
        notification_type=notification_type,
        unread_only=unread_only,
    )
    return APIResponse(code=0, data=result.model_dump(), message="success")


@router.get("/unread-count", summary="获取未读数量")
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取当前用户的未读通知数量"""
    service = NotificationService(db)
    count = await service.get_unread_count(user_id=current_user.id)
    return APIResponse(code=0, data={"unread_count": count}, message="success")


@router.put("/{notification_id}/read", summary="标记已读")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """标记通知为已读"""
    service = NotificationService(db)
    success = await service.mark_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")
    return APIResponse(code=0, data=None, message="已标记为已读")


@router.put("/read-all", summary="全部标记已读")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """标记所有通知为已读"""
    service = NotificationService(db)
    count = await service.mark_all_read(user_id=current_user.id)
    return APIResponse(code=0, data={"marked_count": count}, message="success")


@router.delete("/{notification_id}", summary="删除通知")
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """删除通知"""
    service = NotificationService(db)
    success = await service.delete_notification(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="通知不存在")
    return APIResponse(code=0, data=None, message="通知已删除")


@router.put("/settings", summary="更新通知设置")
async def update_notification_settings(
    settings_data: NotificationSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新通知推送设置"""
    service = NotificationService(db)
    update_kwargs = {
        k: v for k, v in settings_data.model_dump().items() if v is not None
    }
    result = await service.update_settings(
        user_id=current_user.id,
        **update_kwargs,
    )
    return APIResponse(code=0, data=result, message="success")
