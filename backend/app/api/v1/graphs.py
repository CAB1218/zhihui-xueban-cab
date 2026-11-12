"""
AI4Edu 知识图谱 API
提供图谱广场、节点查询、邻居遍历、推荐、misconception管理、跨学科图谱、任务查询等端点
"""
import json
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from urllib.parse import quote as _quote

from app.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.graph import (
    MisconceptionCreate,
    MisconceptionUpdate,
    AutoSuggestResponse,
    GraphChangeCreate,
    GraphReviewAction,
    GraphTaskCreate,
)
from app.services.graph_service import graph_service, SUBJECT_CATEGORIES
from app.services import import_service
from app.services.resource_service import ResourceService
from app.agents.anti_misconception_agent import AntiMisconceptionAgent

router = APIRouter()

# AntiMisconception Agent 实例（用于 AI 辅助标注）
_anti_mc_agent = AntiMisconceptionAgent()

EDITOR_ROLES = {"teacher", "admin", "super_admin"}
EDITOR_DEPENDENCY = require_role(["teacher", "admin", "super_admin"])
_KNOWLEDGE_FILE_TYPES = (".csv", ".xlsx")


async def _apply_graph_change(
    node_id: str,
    change_type: str,
    payload: dict,
    db: AsyncSession,
    tenant_id: Optional[int] = None,
) -> dict:
    """Apply one validated collaborative-edit operation."""
    if not await graph_service.get_node_detail(node_id):
        raise HTTPException(status_code=404, detail="知识节点不存在")

    if change_type == "overview":
        update_data = {
            key: payload[key]
            for key in ("name", "description")
            if key in payload and payload[key] is not None
        }
        if not update_data:
            raise HTTPException(status_code=400, detail="概览没有可更新内容")
        return await graph_service.update_node(node_id, update_data) or {}

    if change_type == "cognitive":
        levels = payload.get("cognitive_level")
        if not isinstance(levels, dict):
            raise HTTPException(status_code=400, detail="认知目标格式错误")
        allowed = {"remember", "understand", "apply", "analyze", "evaluate", "create"}
        clean_levels = {
            key: max(0, min(100, float(value)))
            for key, value in levels.items()
            if key in allowed
        }
        if set(clean_levels) != allowed:
            raise HTTPException(status_code=400, detail="请完整填写六项认知目标")
        result = await graph_service.update_node(
            node_id, {"cognitive_level": json.dumps(clean_levels, ensure_ascii=False)}
        )
        return result or {}

    if change_type in {"relationship", "recommendation"}:
        target_id = str(payload.get("target_id", "")).strip()
        if not target_id or target_id == node_id:
            raise HTTPException(status_code=400, detail="请选择其他知识节点")
        rel_type = "RECOMMENDS" if change_type == "recommendation" else str(payload.get("rel_type", "RELATED"))
        if rel_type not in {"RELATED", "PREREQUISITE", "APPLICATION", "RECOMMENDS"}:
            raise HTTPException(status_code=400, detail="不支持的关系类型")
        result = await graph_service.create_relationship(node_id, target_id, rel_type, payload.get("label"))
        if not result:
            raise HTTPException(status_code=400, detail="目标知识节点不存在")
        return result

    if change_type in {"relationship_delete", "recommendation_delete"}:
        target_id = str(payload.get("target_id", "")).strip()
        rel_type = "RECOMMENDS" if change_type == "recommendation_delete" else str(payload.get("rel_type", "RELATED"))
        await graph_service.delete_relationship(node_id, target_id, rel_type)
        return {"deleted": True}

    resource_service = ResourceService(db)
    if change_type in {"resource_link", "resource_update"}:
        try:
            resource_id = int(payload.get("resource_id"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="资源ID无效")

        resource = await resource_service.get_resource_detail(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="资源不存在")
        if tenant_id is not None and resource.get("tenant_id") != tenant_id:
            raise HTTPException(status_code=403, detail="不能编辑其他租户的资源")

        if change_type == "resource_update":
            allowed_fields = {"title", "description", "tags", "is_public"}
            update_data = {key: value for key, value in payload.items() if key in allowed_fields}
            if not update_data:
                raise HTTPException(status_code=400, detail="资源没有可更新内容")
            await resource_service.update_resource(resource_id, update_data)
            resource = await resource_service.get_resource_detail(resource_id) or resource
        linked = await graph_service.link_resource(node_id, resource)
        return linked or {}

    if change_type == "resource_unlink":
        try:
            resource_id = int(payload.get("resource_id"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="资源ID无效")
        resource = await resource_service.get_resource_detail(resource_id)
        if not resource:
            raise HTTPException(status_code=404, detail="资源不存在")
        if tenant_id is not None and resource.get("tenant_id") != tenant_id:
            raise HTTPException(status_code=403, detail="不能编辑其他租户的资源")
        await graph_service.unlink_resource(node_id, resource_id)
        return {"unlinked": True}

    raise HTTPException(status_code=400, detail="不支持的修改类型")


@router.get("/square", summary="图谱广场")
async def get_square(
    user: User = Depends(get_current_user),
) -> APIResponse:
    """获取学科分类广场统计（12学科 + 节点数 + 完整度 + misconception计数）"""
    stats = await graph_service.get_square_stats()
    return APIResponse(data=stats)


@router.get("/subjects/{subject_id}/graph", summary="获取学科知识图谱")
async def get_subject_graph(
    subject_id: str,
    user: User = Depends(get_current_user),
) -> APIResponse:
    """Return the subject node together with all of its knowledge points."""
    result = await graph_service.get_subject_graph(subject_id)
    if not result["nodes"]:
        raise HTTPException(status_code=404, detail="学科不存在")
    return APIResponse(data=result)


@router.get("/subjects/{subject_id}/nodes/import/template", summary="下载知识点导入模板")
async def knowledge_import_template(
    subject_id: str,
    user: User = Depends(EDITOR_DEPENDENCY),
) -> Response:
    """教师/管理员下载知识点导入模板（CSV，带 BOM）。"""
    return Response(
        content=import_service.knowledge_template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{_quote('知识点导入模板.csv')}"
        },
    )


@router.post("/subjects/{subject_id}/nodes/import", summary="导入知识点（csv / xlsx）")
async def import_knowledge_nodes(
    subject_id: str,
    file: UploadFile = File(...),
    user: User = Depends(EDITOR_DEPENDENCY),
) -> APIResponse:
    """批量导入知识点。

    列：知识点名称（必填）、知识点描述、前置知识点（多个用分号分隔）、关键词。
    同名知识点会跳过；前置知识点可引用本次导入的行，也可以引用学科内已有节点。
    """
    if subject_id not in {s["id"] for s in SUBJECT_CATEGORIES}:
        raise HTTPException(status_code=400, detail="未知学科")

    filename = file.filename or "knowledge.csv"
    if not filename.lower().endswith(_KNOWLEDGE_FILE_TYPES):
        raise HTTPException(status_code=400, detail="仅支持 .csv / .xlsx 文件")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")
    if len(data) > import_service.MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="文件超过 5MB 上限")

    rows, errors = import_service.parse_knowledge_rows(data, filename)
    result = await graph_service.import_nodes(subject_id, rows)
    created = result["created"]
    skipped = result["skipped"]

    return APIResponse(
        data={
            "total": len(rows) + len(errors),
            "created": len(created),
            "skipped": len(skipped),
            "failed": len(errors),
            "links": len(result["links"]),
            "created_rows": created,
            "skipped_rows": skipped,
            "errors": errors[:50],
            "errors_truncated": len(errors) > 50,
            "node_count": len(await graph_service.list_subject_nodes(subject_id)),
        },
        message=(
            f"导入完成：新增 {len(created)} 个知识点，跳过 {len(skipped)} 个，"
            f"{len(errors)} 行未通过校验"
        ),
    )


@router.get("/nodes/{node_id}", summary="获取知识点详情")
async def get_node_detail(
    node_id: str,
    user: User = Depends(get_current_user),
) -> APIResponse:
    """获取知识节点详情"""
    node = await graph_service.get_node_detail(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    return APIResponse(data=node)


@router.get("/nodes/{node_id}/neighbors", summary="获取邻居节点")
async def get_neighbors(
    node_id: str,
    depth: int = Query(1, ge=1, le=3, description="BFS深度"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """BFS获取节点的邻居子图"""
    result = await graph_service.get_neighbors(node_id, depth=depth, limit=limit)
    return APIResponse(data=result)


@router.get("/nodes/{node_id}/resources", summary="获取节点关联资源")
async def get_node_resources(
    node_id: str,
    user: User = Depends(get_current_user),
) -> APIResponse:
    """获取知识点关联的资源列表"""
    resources = await graph_service.get_node_resources(node_id)
    return APIResponse(data=resources)


@router.get("/nodes/{node_id}/recommendations", summary="获取推荐节点")
async def get_node_recommendations(
    node_id: str,
    limit: int = Query(10, ge=1, le=50, description="推荐数量"),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """基于同路径、同学科和跨学科关联获取推荐节点"""
    recommendations = await graph_service.get_recommendations(node_id, limit=limit)
    return APIResponse(data=recommendations)


@router.get("/nodes/{node_id}/cognitive", summary="获取认知目标")
async def get_cognitive_goals(
    node_id: str,
    include_avg: bool = Query(False, description="是否包含学科均值"),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """获取节点的认知目标雷达图数据（六维）"""
    data = await graph_service.get_cognitive_goals(node_id, include_avg=include_avg)
    if not data:
        raise HTTPException(status_code=404, detail="节点不存在")
    return APIResponse(data=data)


@router.post("/nodes", summary="创建知识节点")
async def create_node(
    id: Optional[str] = Query(None, description="节点ID；留空时自动生成"),
    name: str = Query(..., description="节点名称"),
    subject: str = Query(..., description="学科分类"),
    description: Optional[str] = Query(None, description="节点描述"),
    cognitive_level: Optional[str] = Query(None, description="认知水平JSON"),
    has_misconception: bool = Query(False, description="是否有误解标注"),
    misconceptions: Optional[str] = Query(None, description="误解标注JSON"),
    user: User = Depends(EDITOR_DEPENDENCY),
) -> APIResponse:
    """创建新的知识节点（教师或超级管理员）"""
    node_id = id or f"{subject}_{uuid.uuid4().hex[:12]}"
    node_data: dict = {"id": node_id, "name": name, "subject": subject, "node_type": "knowledge"}
    if description:
        node_data["description"] = description
    if cognitive_level:
        node_data["cognitive_level"] = cognitive_level
    node_data["has_misconception"] = has_misconception
    if misconceptions:
        node_data["misconceptions"] = misconceptions

    node = await graph_service.create_node(node_data)
    return APIResponse(data=node, message="节点创建成功")


@router.put("/nodes/{node_id}", summary="更新知识节点")
async def update_node(
    node_id: str,
    name: Optional[str] = Query(None, description="节点名称"),
    description: Optional[str] = Query(None, description="节点描述"),
    cognitive_level: Optional[str] = Query(None, description="认知水平JSON"),
    has_misconception: Optional[bool] = Query(None, description="是否有误解标注"),
    misconceptions: Optional[str] = Query(None, description="误解标注JSON"),
    user: User = Depends(EDITOR_DEPENDENCY),
) -> APIResponse:
    """更新知识节点属性（教师+权限）"""
    update_data: dict = {}
    if name is not None:
        update_data["name"] = name
    if description is not None:
        update_data["description"] = description
    if cognitive_level is not None:
        update_data["cognitive_level"] = cognitive_level
    if has_misconception is not None:
        update_data["has_misconception"] = has_misconception
    if misconceptions is not None:
        update_data["misconceptions"] = misconceptions

    if not update_data:
        raise HTTPException(status_code=400, detail="未提供更新数据")

    node = await graph_service.update_node(node_id, update_data)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")
    return APIResponse(data=node, message="节点更新成功")


@router.delete("/nodes/{node_id}", summary="删除知识节点")
async def delete_node(
    node_id: str,
    user: User = Depends(EDITOR_DEPENDENCY),
) -> APIResponse:
    """删除知识节点及其审核申请、图谱任务和所有关系。"""
    deleted = await graph_service.delete_node(node_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="节点不存在")
    return APIResponse(message="知识点已删除")


@router.post("/nodes/{from_id}/link/{to_id}", summary="创建节点关系")
async def create_relationship(
    from_id: str,
    to_id: str,
    rel_type: str = Query("RELATED", description="关系类型"),
    label: Optional[str] = Query(None, description="关系标签"),
    user: User = Depends(EDITOR_DEPENDENCY),
) -> APIResponse:
    """创建两个知识节点之间的关系（教师+权限）"""
    result = await graph_service.create_relationship(from_id, to_id, rel_type, label)
    if not result:
        raise HTTPException(status_code=400, detail="创建关系失败，请检查节点是否存在")
    return APIResponse(data=result, message="关系创建成功")


@router.delete("/nodes/{from_id}/link/{to_id}", summary="删除节点关系")
async def delete_relationship(
    from_id: str,
    to_id: str,
    rel_type: str = Query("RELATED", description="关系类型"),
    user: User = Depends(EDITOR_DEPENDENCY),
) -> APIResponse:
    """删除两个知识节点之间的关系（教师+权限）"""
    await graph_service.delete_relationship(from_id, to_id, rel_type)
    return APIResponse(message="关系删除成功")


@router.get("/search", summary="搜索知识节点")
async def search_nodes(
    q: str = Query("", description="搜索关键词；为空时按学科列出节点"),
    subject: Optional[str] = Query(None, description="学科筛选"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """搜索知识节点"""
    results = await graph_service.search_nodes(q, subject=subject, limit=limit)
    return APIResponse(data=results)


# ==================== 协作编辑与教师审核 ====================

@router.post("/nodes/{node_id}/changes", summary="提交图谱详情修改")
async def submit_graph_change(
    node_id: str,
    body: GraphChangeCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """Teachers/admins apply immediately; student changes enter the review queue."""
    if user.role in EDITOR_ROLES:
        applied = await _apply_graph_change(
            node_id,
            body.change_type,
            body.payload,
            db,
            None if user.role == "super_admin" else user.tenant_id,
        )
        return APIResponse(
            data={"status": "approved", "applied": applied},
            message="修改已生效",
        )

    request = await graph_service.create_change_request(
        node_id=node_id,
        change_type=body.change_type,
        payload=body.payload,
        submitted_by=user.id,
        tenant_id=user.tenant_id,
    )
    return APIResponse(
        data=request,
        message="修改已提交，等待教师审核",
    )


@router.get("/change-requests", summary="获取图谱修改审核列表")
async def list_graph_change_requests(
    status_filter: str = Query("pending", alias="status"),
    node_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
) -> APIResponse:
    if status_filter not in {"pending", "approved", "rejected"}:
        raise HTTPException(status_code=400, detail="审核状态无效")
    requests = await graph_service.list_change_requests(
        status_filter=status_filter,
        node_id=node_id,
        tenant_id=user.tenant_id if user.role != "super_admin" else None,
        submitted_by=None if user.role in EDITOR_ROLES else user.id,
    )
    return APIResponse(data=requests)


@router.post("/change-requests/{request_id}/review", summary="审核图谱修改")
async def review_graph_change(
    request_id: str,
    body: GraphReviewAction,
    user: User = Depends(EDITOR_DEPENDENCY),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    request = await graph_service.get_change_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="审核申请不存在")
    if request.get("status") != "pending":
        raise HTTPException(status_code=409, detail="该申请已经审核")
    if user.role != "super_admin" and request.get("tenant_id") != user.tenant_id:
        raise HTTPException(status_code=403, detail="不能审核其他租户的申请")

    applied = None
    new_status = "approved" if body.approved else "rejected"
    if body.approved:
        applied = await _apply_graph_change(
            request["node_id"], request["change_type"], request.get("payload", {}), db,
            request.get("tenant_id"),
        )
    updated = await graph_service.finish_change_request(
        request_id, new_status, user.id, body.comment
    )
    return APIResponse(
        data={"request": updated, "applied": applied},
        message="审核通过，修改已生效" if body.approved else "申请已驳回",
    )


# ==================== Misconception 端点 ====================

@router.get("/nodes/{node_id}/misconceptions", summary="获取节点误解标注")
async def get_misconceptions(
    node_id: str,
    user: User = Depends(get_current_user),
) -> APIResponse:
    """获取节点的误解标注列表（全体用户可访问）"""
    misconceptions = await graph_service.get_misconceptions(node_id)
    return APIResponse(data=misconceptions)


@router.post("/nodes/{node_id}/misconceptions", summary="添加误解标注")
async def add_misconception(
    node_id: str,
    body: MisconceptionCreate,
    user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
) -> APIResponse:
    """添加误解标注（教师+权限）"""
    # 验证节点存在
    node = await graph_service.get_node_detail(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    data = body.model_dump()
    mc = await graph_service.add_misconception(node_id, data, user.id)
    return APIResponse(data=mc, message="误解标注添加成功")


@router.put("/nodes/{node_id}/misconceptions/{mc_id}", summary="编辑误解标注")
async def update_misconception(
    node_id: str,
    mc_id: str,
    body: MisconceptionUpdate,
    user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
) -> APIResponse:
    """编辑误解标注（教师+权限）"""
    data = body.model_dump(exclude_none=True)
    if not data:
        raise HTTPException(status_code=400, detail="未提供更新数据")

    mc = await graph_service.update_misconception(node_id, mc_id, data)
    if not mc:
        raise HTTPException(status_code=404, detail="误解标注不存在")
    return APIResponse(data=mc, message="误解标注更新成功")


@router.delete("/nodes/{node_id}/misconceptions/{mc_id}", summary="删除误解标注")
async def delete_misconception(
    node_id: str,
    mc_id: str,
    user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
) -> APIResponse:
    """删除误解标注（教师+权限）"""
    success = await graph_service.delete_misconception(node_id, mc_id)
    if not success:
        raise HTTPException(status_code=404, detail="误解标注不存在")
    return APIResponse(message="删除成功")


@router.post("/nodes/{node_id}/misconceptions/auto-suggest", summary="AI辅助标注建议")
async def auto_suggest_misconceptions(
    node_id: str,
    user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
) -> APIResponse:
    """AI辅助标注建议（教师+权限）"""
    # 获取节点详情
    node = await graph_service.get_node_detail(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="节点不存在")

    node_name = node.get("name", "")
    node_desc = node.get("description", "") or ""
    node_subject = node.get("subject", "")

    # 调用 Agent 获取建议
    suggestions = _anti_mc_agent.suggest_for_node(node_name, node_desc, node_subject)

    response = AutoSuggestResponse(
        suggestions=suggestions,
        total=len(suggestions),
    )
    return APIResponse(data=response.model_dump())


# ==================== 任务端点 ====================

@router.get("/nodes/{node_id}/tasks", summary="获取节点关联任务")
async def get_node_tasks(
    node_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取节点关联的学习任务（全体用户可访问）"""
    tasks = await graph_service.get_node_tasks(
        node_id, db, user_id=user.id, tenant_id=user.tenant_id
    )
    return APIResponse(data=tasks)


@router.post("/nodes/{node_id}/tasks", summary="布置知识点任务")
async def create_node_task(
    node_id: str,
    body: GraphTaskCreate,
    user: User = Depends(EDITOR_DEPENDENCY),
) -> APIResponse:
    task = await graph_service.create_graph_task(
        node_id=node_id,
        data=body.model_dump(mode="json"),
        assigned_by=user.id,
        tenant_id=user.tenant_id,
    )
    if not task:
        raise HTTPException(status_code=404, detail="知识节点不存在")
    return APIResponse(data=task, message="任务已布置")


# ==================== 跨学科图谱端点 ====================

@router.get("/cross-subject", summary="跨学科关联图谱")
async def get_cross_subject_graph(
    subjects: str = Query(..., description="学科ID列表，逗号分隔，如 math,physics"),
    min_strength: float = Query(0.0, ge=0.0, le=1.0, description="最小关系强度阈值"),
    max_nodes: int = Query(100, ge=10, le=500, description="最大节点数"),
    user: User = Depends(get_current_user),
) -> APIResponse:
    """获取跨学科知识点关联网络（全体用户可访问）"""
    subject_list = [s.strip() for s in subjects.split(",") if s.strip()]
    if len(subject_list) < 2:
        raise HTTPException(status_code=400, detail="至少需要选择2个学科")

    result = await graph_service.get_cross_subject_graph(
        subjects=subject_list,
        min_strength=min_strength,
        max_nodes=max_nodes,
    )
    return APIResponse(data=result)
