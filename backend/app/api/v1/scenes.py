"""
智慧学伴 场景 API
提供场景切换、推荐、配置等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.scene import (
    SceneConfigResponse,
    SceneRecommendation,
    SceneSwitchRequest,
    SceneSwitchResponse,
)
from app.schemas.common import APIResponse
from app.database import get_db
from app.services.scene_service import SceneService
from app.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("/current", response_model=APIResponse[SceneConfigResponse], summary="获取当前场景")
async def get_current_scene(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[SceneConfigResponse]:
    """获取用户当前激活的场景及配置"""
    scene_service = SceneService(db)
    result = await scene_service.get_current_scene(current_user.id)
    return APIResponse(data=result)


@router.post("/switch", response_model=APIResponse[SceneSwitchResponse], summary="切换场景")
async def switch_scene(
    request: SceneSwitchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[SceneSwitchResponse]:
    """
    切换当前场景

    - 更新用户当前场景偏好
    - 返回新场景完整配置（布局、功能开关、组件）
    - 记录场景切换事件
    """
    scene_service = SceneService(db)
    result = await scene_service.switch_scene(current_user.id, request)
    return APIResponse(data=result)


@router.get("/recommendation", response_model=APIResponse[SceneRecommendation], summary="获取场景推荐")
async def get_scene_recommendation(
    context: Optional[str] = Query(None, description="上下文信息"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> APIResponse[SceneRecommendation]:
    """
    基于时间、课程表、学习行为推荐最佳场景

    - 分析当前时间段和课程安排
    - 根据历史行为偏好推荐
    - 返回推荐场景及理由
    - 区分工作日/周末推荐策略
    """
    scene_service = SceneService(db)
    result = await scene_service.get_recommendation(current_user.id, context)
    return APIResponse(data=result)


@router.get("/{scene_type}/config", response_model=APIResponse[SceneConfigResponse], summary="获取场景配置")
async def get_scene_config(
    scene_type: str,
    db: AsyncSession = Depends(get_db),
) -> APIResponse[SceneConfigResponse]:
    """
    获取指定场景类型的完整配置

    包括主题色、布局、功能开关、默认组件、AI 提示词模板
    """
    scene_service = SceneService(db)
    result = await scene_service.get_scene_config(scene_type)
    return APIResponse(data=result)


@router.get("/list", response_model=APIResponse[list], summary="获取场景列表")
async def list_scenes(
    db: AsyncSession = Depends(get_db),
) -> APIResponse[list]:
    """获取所有可用场景列表"""
    scene_service = SceneService(db)
    result = await scene_service.list_scenes()
    return APIResponse(data=result)
