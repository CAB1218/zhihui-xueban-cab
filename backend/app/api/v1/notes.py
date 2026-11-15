"""
智慧学伴 笔记 API
提供笔记 CRUD、AI增强、版本管理等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginationParams
from app.schemas.note import AIEnhanceRequest, AIEnhanceResponse, NoteCreate, NoteUpdate, ShareResponse
from app.services.note_service import NoteService
from app.services.search_service import search_service

router = APIRouter()


@router.get("", include_in_schema=False)
@router.get("/", summary="获取笔记列表")
async def list_notes(
    pagination: PaginationParams = Depends(),
    course_id: Optional[int] = Query(None, description="课程ID筛选"),
    note_type: Optional[str] = Query(None, description="笔记类型"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取笔记列表，支持分页和筛选"""
    service = NoteService(db)
    result = await service.list_notes(
        tenant_id=current_user.tenant_id or 0,
        owner_id=current_user.id,
        pagination=pagination,
        course_id=course_id,
        note_type=note_type,
        search=search,
    )
    return APIResponse(data=result.model_dump(), message="success")


@router.post("", include_in_schema=False)
@router.post("/", summary="创建笔记")
async def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """创建新笔记"""
    service = NoteService(db)
    result = await service.create_note(
        tenant_id=current_user.tenant_id or 0,
        owner_id=current_user.id,
        title=note_data.title,
        content=note_data.content,
        content_plain=note_data.content_plain,
        note_type=note_data.note_type,
        course_id=note_data.course_id,
        resource_id=note_data.resource_id,
        tags=note_data.tags,
        is_encrypted=note_data.is_encrypted,
    )
    # E2E 加密笔记不发送到外部搜索索引；普通笔记索引失败也不影响保存。
    if not note_data.is_encrypted:
        await search_service.index_note(result)
    return APIResponse(data=result, message="success")


@router.get("/{note_id}", summary="获取笔记详情")
async def get_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取笔记详情（含内容和元数据）"""
    service = NoteService(db)
    result = await service.get_note(
        note_id=note_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return APIResponse(data=result, message="success")


@router.put("/{note_id}", summary="更新笔记")
async def update_note(
    note_id: int,
    note_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新笔记内容"""
    service = NoteService(db)
    result = await service.update_note(
        note_id=note_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        title=note_data.title,
        content=note_data.content,
        content_plain=note_data.content_plain,
        tags=note_data.tags,
        change_summary=note_data.change_summary,
        bypass_owner_check=current_user.role == "super_admin",
    )
    if not result:
        raise HTTPException(status_code=404, detail="笔记不存在或无权修改")
    await search_service.index_note(result)
    return APIResponse(data=result, message="success")


@router.delete("/{note_id}", summary="删除笔记")
async def delete_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """软删除笔记"""
    service = NoteService(db)
    success = await service.delete_note(
        note_id=note_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        bypass_owner_check=current_user.role == "super_admin",
    )
    if not success:
        raise HTTPException(status_code=404, detail="笔记不存在")
    await search_service.delete_document("note", note_id)
    return APIResponse(data=None, message="笔记已删除")


@router.post("/{note_id}/ai-enhance", summary="AI增强笔记")
async def ai_enhance_note(
    note_id: int,
    enhance_request: AIEnhanceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """使用AI增强笔记（摘要、纠错、补充知识点）"""
    service = NoteService(db)
    result = await service.ai_enhance(
        note_id=note_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        enhance_type=enhance_request.enhance_type,
        additional_instructions=enhance_request.additional_instructions,
    )
    return APIResponse(data=result, message="success")


@router.get("/{note_id}/versions", summary="获取笔记版本历史")
async def list_note_versions(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取笔记的版本历史"""
    service = NoteService(db)
    result = await service.list_versions(
        note_id=note_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(data=result, message="success")


@router.post("/{note_id}/share", summary="分享笔记")
async def share_note(
    note_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """生成笔记分享链接"""
    service = NoteService(db)
    result = await service.share_note(
        note_id=note_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        bypass_owner_check=current_user.role == "super_admin",
    )
    return APIResponse(data=result, message="success")
