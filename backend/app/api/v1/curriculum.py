"""
AI4EDU 课程梳理 API
任务1：用户输入课程 → 联网检索+LLM 梳理 → 学习内容与要求清单/必要联系/材料出处
支持 JSON / Markdown / Word 三格式导出
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.curriculum import (
    CurriculumOutlineResponse,
    OutlineGenerateRequest,
)
from app.services.curriculum_service import CurriculumService

router = APIRouter()


def _to_response(record) -> CurriculumOutlineResponse:
    """DB 记录 → 响应（outline 字段反序列化为结构化对象）"""
    import json

    from app.schemas.curriculum import CurriculumOutlineData

    outline_obj = None
    if record.outline:
        try:
            outline_obj = CurriculumOutlineData.model_validate_json(record.outline)
        except Exception:  # noqa: BLE001 — 历史脏数据兜底
            outline_obj = None
    return CurriculumOutlineResponse(
        id=record.id,
        course_query=record.course_query,
        subject=record.subject,
        grade_level=record.grade_level,
        scope_hint=record.scope_hint,
        title=record.title,
        outline=outline_obj,
        model_name=record.model_name,
        used_web_search=record.used_web_search,
        status=record.status,
        error_message=record.error_message,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


@router.post("/outlines", summary="生成课程梳理大纲")
async def generate_outline(
    data: OutlineGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CurriculumOutlineResponse]:
    """用户开局输入想学的课程，系统联网检索并依据课程标准梳理出
    学习内容与要求清单、必要联系、材料出处（约需 30-90 秒）"""
    service = CurriculumService(db)
    record = await service.generate_outline(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id or 0,
        data=data,
    )
    return APIResponse(data=_to_response(record), message="生成成功" if record.status == "completed" else "生成失败")


@router.get("/outlines", summary="获取我的课程梳理记录列表")
async def list_outlines(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PaginatedResponse[CurriculumOutlineResponse]]:
    """当前用户的课程梳理历史"""
    service = CurriculumService(db)
    rows, total = await service.list_outlines(user_id=current_user.id, page=page, page_size=page_size)
    return APIResponse(
        data=PaginatedResponse(
            items=[_to_response(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="success",
    )


@router.get("/outlines/{outline_id}", summary="获取课程梳理详情")
async def get_outline(
    outline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CurriculumOutlineResponse]:
    """查看某次课程梳理的完整大纲"""
    service = CurriculumService(db)
    record = await service.get_outline(outline_id, current_user.id, is_admin=_is_admin(current_user))
    return APIResponse(data=_to_response(record), message="success")


@router.get("/outlines/{outline_id}/export", summary="导出课程梳理（json/md/docx）")
async def export_outline(
    outline_id: int,
    format: Optional[str] = Query("md", pattern="^(json|md|docx)$", description="导出格式"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """下载学习内容与要求梳理成果：
    json 供学情分析模块消费，md 便于在线阅读，docx 便于提交打印"""
    service = CurriculumService(db)
    content, filename, media_type = await service.export_outline(
        outline_id, current_user.id, format or "md", is_admin=_is_admin(current_user)
    )
    from urllib.parse import quote

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


def _is_admin(user: User) -> bool:
    return getattr(user, "role", "") in {"admin", "super_admin"}
