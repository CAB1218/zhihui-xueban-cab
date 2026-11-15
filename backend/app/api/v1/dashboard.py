"""
智慧学伴 仪表盘统计 API
返回当前用户的课程数、笔记数、资源数、学习时长、AI对话数等
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.database import get_db
from app.schemas.common import APIResponse
from app.dependencies import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/dashboard/stats", summary="获取仪表盘统计数据")
async def get_dashboard_stats(
    current_user: Any = Depends(get_current_user),
    db=Depends(get_db),
) -> APIResponse:
    """
    获取当前用户的仪表盘统计：
    - 课程数（已选课）
    - 笔记数
    - 资源数
    - AI对话数
    - 学习时长（占位，后续可接入 ClickHouse 学习时长统计）
    """
    user_id = current_user.id
    tenant_id = getattr(current_user, "tenant_id", None)

    # 课程数：通过选课表统计
    course_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM course_enrollments "
            "WHERE user_id = :uid AND dropped_at IS NULL"
        ),
        {"uid": user_id},
    )
    course_count = course_result.scalar() or 0

    # 笔记数
    note_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM notes "
            "WHERE owner_id = :uid AND is_deleted = false"
        ),
        {"uid": user_id},
    )
    note_count = note_result.scalar() or 0

    # 资源数（该租户下公开资源）
    resource_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM resources "
            "WHERE tenant_id = :tid AND is_active = true"
        ),
        {"tid": tenant_id},
    )
    resource_count = resource_result.scalar() or 0

    # AI 对话数
    ai_chat_result = await db.execute(
        text(
            "SELECT COUNT(*) FROM agent_sessions "
            "WHERE user_id = :uid"
        ),
        {"uid": user_id},
    )
    ai_chat_count = ai_chat_result.scalar() or 0

    stats = {
        "course_count": course_count,
        "note_count": note_count,
        "resource_count": resource_count,
        "ai_chat_count": ai_chat_count,
        "study_hours": "12.5h",
    }

    return APIResponse(data=stats)
