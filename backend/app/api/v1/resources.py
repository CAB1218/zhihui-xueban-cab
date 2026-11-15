"""
智慧学伴 资源 API
提供资源上传、列表、详情、删除、关联知识点、AI标签、AI摘要、预览等端点
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user, require_role
from app.models.user import User
from app.schemas.common import APIResponse, PaginationParams
from app.services.resource_service import ResourceService

router = APIRouter()


class LinkResourceCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    url: HttpUrl
    description: Optional[str] = Field(None, max_length=2000)


@router.post("/upload", summary="上传资源")
async def upload_resource(
    file: UploadFile = File(..., description="上传文件"),
    title: Optional[str] = Form(None, description="资源标题"),
    description: Optional[str] = Form(None, description="资源描述"),
    resource_type: Optional[str] = Form(None, description="资源类型"),
    course_id: Optional[int] = Form(None, description="关联课程ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """上传新资源（多文件支持，MinIO存储）"""
    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="文件不能为空")

    service = ResourceService(db)
    result = await service.upload_file(
        file_data=file_data,
        filename=file.filename or "unknown",
        content_type=file.content_type or "application/octet-stream",
        uploader_id=current_user.id,
        tenant_id=current_user.tenant_id,
        title=title,
        description=description,
        resource_type=resource_type,
        course_id=course_id,
    )
    return APIResponse(data=result, message="上传成功")


@router.post("/link", summary="创建网页链接资源")
async def create_link_resource(
    body: LinkResourceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Create a resource backed by an HTTPS/HTTP web link."""
    service = ResourceService(db)
    result = await service.create_link_resource(
        url=str(body.url),
        title=body.title,
        description=body.description,
        uploader_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    return APIResponse(data=result, message="链接资源创建成功")


@router.get("/list", summary="获取资源列表")
async def list_resources(
    pagination: PaginationParams = Depends(),
    resource_type: Optional[str] = Query(None, description="资源类型筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取资源列表，支持分页、类型筛选和搜索"""
    service = ResourceService(db)
    result = await service.list_resources(
        pagination,
        resource_type=resource_type,
        uploader_id=current_user.id,
        search=search,
        tenant_id=current_user.tenant_id,
    )
    return APIResponse(data=result)


@router.get("/{resource_id}", summary="获取资源详情")
async def get_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取单个资源的详细信息"""
    service = ResourceService(db)
    result = await service.get_resource_detail(resource_id)
    if not result:
        raise HTTPException(status_code=404, detail="资源不存在")
    return APIResponse(data=result)


@router.put("/{resource_id}", summary="更新资源信息")
async def update_resource(
    resource_id: int,
    title: Optional[str] = Query(None, description="资源标题"),
    description: Optional[str] = Query(None, description="资源描述"),
    tags: Optional[str] = Query(None, description="标签JSON数组"),
    is_public: Optional[bool] = Query(None, description="是否公开"),
    current_user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新资源元信息"""
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if tags is not None:
        update_data["tags"] = tags
    if is_public is not None:
        update_data["is_public"] = is_public

    service = ResourceService(db)
    existing = await service.get_resource_detail(resource_id)
    if not existing:
        raise HTTPException(status_code=404, detail="资源不存在")
    if current_user.role != "super_admin" and existing.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="不能编辑其他租户的资源")
    result = await service.update_resource(resource_id, update_data)
    if not result:
        raise HTTPException(status_code=404, detail="资源不存在")
    return APIResponse(data=result, message="更新成功")


@router.delete("/{resource_id}", summary="删除资源")
async def delete_resource(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """软删除资源"""
    service = ResourceService(db)
    success = await service.delete_resource(resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="资源不存在")
    return APIResponse(message="删除成功")


@router.post("/{resource_id}/link-node", summary="关联知识点")
async def link_to_node(
    resource_id: int,
    node_id: str = Query(..., description="知识节点ID"),
    current_user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """关联资源到知识节点"""
    service = ResourceService(db)
    existing = await service.get_resource_detail(resource_id)
    if not existing:
        raise HTTPException(status_code=404, detail="资源不存在")
    if current_user.role != "super_admin" and existing.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="不能关联其他租户的资源")
    success = await service.link_to_node(resource_id, node_id)
    if not success:
        raise HTTPException(status_code=404, detail="资源不存在")
    return APIResponse(message="关联成功")


@router.delete("/{resource_id}/link-node/{node_id}", summary="取消关联知识点")
async def unlink_from_node(
    resource_id: int,
    node_id: str,
    current_user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """取消关联资源到知识节点"""
    service = ResourceService(db)
    existing = await service.get_resource_detail(resource_id)
    if not existing:
        raise HTTPException(status_code=404, detail="资源不存在")
    if current_user.role != "super_admin" and existing.get("tenant_id") != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="不能取消其他租户的资源关联")
    success = await service.unlink_from_node(resource_id, node_id)
    if not success:
        raise HTTPException(status_code=404, detail="资源或关联不存在")
    return APIResponse(message="取消关联成功")


@router.get("/{resource_id}/preview", summary="资源预览")
async def preview_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取资源预览URL（MinIO预签名）"""
    service = ResourceService(db)
    detail = await service.get_resource_detail(resource_id)
    if not detail:
        raise HTTPException(status_code=404, detail="资源不存在")

    preview_url = detail.get("preview_url")
    if not preview_url:
        raise HTTPException(status_code=400, detail="预览不可用")

    return APIResponse(data={"preview_url": preview_url})


@router.post("/{resource_id}/auto-tag", summary="AI自动标签")
async def auto_tag(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """AI 自动为资源生成标签"""
    service = ResourceService(db)
    tags = await service.auto_tag(resource_id)
    return APIResponse(data={"tags": tags}, message="标签生成成功")


@router.post("/{resource_id}/summarize", summary="AI生成摘要")
async def summarize(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """AI 生成资源摘要"""
    service = ResourceService(db)
    summary = await service.generate_summary(resource_id)
    return APIResponse(data={"summary": summary}, message="摘要生成成功")


@router.post("/{resource_id}/favorite", summary="收藏/取消收藏")
async def toggle_favorite(
    resource_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """切换资源的收藏状态"""
    from app.repositories.resource_repo import ResourceRepository

    repo = ResourceRepository(db)
    is_favorited = await repo.toggle_favorite(current_user.id, resource_id)
    action = "收藏" if is_favorited else "取消收藏"
    return APIResponse(data={"is_favorited": is_favorited}, message=f"{action}成功")
