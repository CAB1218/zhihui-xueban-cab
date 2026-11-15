"""
智慧学伴 学伴 API
提供学伴配置、互动、学习报告等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.services.buddy_service import BuddyService

router = APIRouter()


class ChatRequest(BaseModel):
    """学伴对话请求"""

    message: str = Field(..., description="消息内容", min_length=1)


class UpdateBuddyProfile(BaseModel):
    """更新学伴配置请求"""

    name: Optional[str] = Field(None, description="学伴名称", max_length=50)
    personality: Optional[str] = Field(None, description="人设: encouraging/strict/humorous/gentle")
    tone: Optional[str] = Field(None, description="语气: friendly/formal/casual")
    interaction_mode: Optional[str] = Field(None, description="互动模式: proactive/passive/balanced")
    avatar_url: Optional[str] = Field(None, description="头像URL")
    custom_prompt: Optional[str] = Field(None, description="自定义提示词")


class EncourageRequest(BaseModel):
    """鼓励互动请求"""

    action: str = Field("praise", description="互动类型: praise/pet/high_five")


@router.get("/profile", summary="获取学伴信息")
async def get_buddy_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取当前用户的学伴配置和信息"""
    service = BuddyService(db)
    result = await service.get_or_create_profile(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.put("/profile", summary="更新学伴配置")
async def update_buddy_profile(
    profile_data: UpdateBuddyProfile,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新学伴人设、语气、互动模式等配置"""
    service = BuddyService(db)
    result = await service.update_profile(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        name=profile_data.name,
        personality=profile_data.personality,
        tone=profile_data.tone,
        interaction_mode=profile_data.interaction_mode,
        avatar_url=profile_data.avatar_url,
        custom_prompt=profile_data.custom_prompt,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/daily-report", summary="每日学伴报告")
async def get_daily_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取学伴每日学习报告"""
    service = BuddyService(db)
    result = await service.get_daily_report(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/chat", summary="学伴对话")
async def chat_with_buddy(
    chat_data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """与学伴进行对话"""
    service = BuddyService(db)
    result = await service.chat(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        message=chat_data.message,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/mood", summary="获取学伴心情")
async def get_buddy_mood(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取学伴当前心情状态"""
    service = BuddyService(db)
    result = await service.get_mood(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/encourage", summary="鼓励互动")
async def encourage_buddy(
    encourage_data: EncourageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """与学伴互动（鼓励、点赞等）"""
    service = BuddyService(db)
    result = await service.encourage(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        action=encourage_data.action,
    )
    return APIResponse(code=0, data=result, message="success")
