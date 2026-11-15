"""
智慧学伴 对话导出 API 端点
支持将 AI 会话导出为 PDF / Markdown 格式。

端点:
- POST   /agents/sessions/{session_id}/exports      创建导出任务
- GET    /agents/sessions/{session_id}/exports       获取会话的导出列表
- GET    /agents/exports/{export_id}                 获取导出详情
- GET    /agents/exports/{export_id}/download        获取预签名下载 URL
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from app.models.agent import AgentSession
from app.models.export import AgentExport
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.export import ExportCreate, ExportDownloadResponse, ExportResponse

logger = logging.getLogger(__name__)

router = APIRouter()


# ============ 依赖注入辅助 ============

async def _get_db_dep():
    """获取异步数据库会话"""
    from app.database import get_db

    async for session in get_db():
        yield session


# ============ 端点 ============


@router.post(
    "/sessions/{session_id}/exports",
    summary="创建对话导出任务",
    status_code=status.HTTP_201_CREATED,
)
async def create_export(
    session_id: int,
    export_data: ExportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db_dep),
) -> APIResponse:
    """创建对话导出任务

    1. 校验会话归属
    2. 创建 AgentExport 记录（status=pending）
    3. 触发 Celery 异步任务
    4. 返回导出记录信息

    支持格式:
    - **markdown**: 纯文本 Markdown
    - **pdf**: PDF 文档（使用 reportlab 渲染）
    """
    # 校验格式
    fmt = export_data.export_format.lower()
    if fmt not in ("pdf", "markdown"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="export_format 必须为 pdf 或 markdown",
        )

    # 校验会话归属
    session_stmt = select(AgentSession).where(
        AgentSession.id == session_id,
        AgentSession.user_id == current_user.id,
    )
    session_result = await db.execute(session_stmt)
    session = session_result.scalars().first()

    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 创建导出记录
    from app.services.agent_export_service import AgentExportService

    export_service = AgentExportService(db)
    export_record = await export_service.create_export_record(
        session_id=session_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        export_format=fmt,
    )

    export_id = export_record.id

    # 触发 Celery 任务
    try:
        from app.tasks.export_tasks import export_session_task

        export_session_task.delay(export_id)
    except Exception as e:
        logger.warning("Celery 导出任务触发失败（不影响记录创建）: %s", e)

    return APIResponse(
        code=0,
        data=ExportResponse(
            id=export_record.id,
            session_id=export_record.session_id,
            export_format=export_record.export_format,
            status=export_record.status,
            file_size=export_record.file_size,
            error_msg=export_record.error_msg,
            created_at=export_record.created_at.isoformat()
            if export_record.created_at
            else None,
            completed_at=export_record.completed_at.isoformat()
            if export_record.completed_at
            else None,
            expired_at=export_record.expired_at.isoformat()
            if export_record.expired_at
            else None,
        ).model_dump(),
        message="导出任务已创建，请稍后查看状态",
    )


@router.get(
    "/sessions/{session_id}/exports",
    summary="获取会话的导出列表",
)
async def list_exports(
    session_id: int,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db_dep),
) -> APIResponse:
    """获取指定会话的导出记录列表"""
    # 校验会话归属
    session_stmt = select(AgentSession).where(
        AgentSession.id == session_id,
        AgentSession.user_id == current_user.id,
    )
    session_result = await db.execute(session_stmt)
    if not session_result.scalars().first():
        raise HTTPException(status_code=404, detail="会话不存在")

    # 查询导出记录
    from sqlalchemy import func

    conditions = [
        AgentExport.session_id == session_id,
        AgentExport.user_id == current_user.id,
    ]

    count_stmt = select(func.count(AgentExport.id)).where(*conditions)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    offset = (page - 1) * page_size
    stmt = (
        select(AgentExport)
        .where(*conditions)
        .order_by(desc(AgentExport.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    exports = result.scalars().all()

    items = [
        ExportResponse(
            id=e.id,
            session_id=e.session_id,
            export_format=e.export_format,
            status=e.status,
            file_size=e.file_size,
            error_msg=e.error_msg,
            created_at=e.created_at.isoformat() if e.created_at else None,
            completed_at=e.completed_at.isoformat() if e.completed_at else None,
            expired_at=e.expired_at.isoformat() if e.expired_at else None,
        ).model_dump()
        for e in exports
    ]

    return APIResponse(
        code=0,
        data=PaginatedResponse(
            items=items, total=total, page=page, page_size=page_size
        ),
        message="success",
    )


@router.get(
    "/exports/{export_id}",
    summary="获取导出详情",
)
async def get_export(
    export_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db_dep),
) -> APIResponse:
    """获取导出记录详情"""
    stmt = select(AgentExport).where(
        AgentExport.id == export_id,
        AgentExport.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    export_record = result.scalars().first()

    if not export_record:
        raise HTTPException(status_code=404, detail="导出记录不存在")

    return APIResponse(
        code=0,
        data=ExportResponse(
            id=export_record.id,
            session_id=export_record.session_id,
            export_format=export_record.export_format,
            status=export_record.status,
            file_size=export_record.file_size,
            error_msg=export_record.error_msg,
            created_at=export_record.created_at.isoformat()
            if export_record.created_at
            else None,
            completed_at=export_record.completed_at.isoformat()
            if export_record.completed_at
            else None,
            expired_at=export_record.expired_at.isoformat()
            if export_record.expired_at
            else None,
        ).model_dump(),
        message="success",
    )


@router.get(
    "/exports/{export_id}/download",
    summary="获取下载链接",
)
async def download_export(
    export_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(_get_db_dep),
) -> APIResponse:
    """获取导出文件的预签名下载 URL

    仅当导出状态为 completed 时可下载。
    URL 有效期由 settings.EXPORT_PRESIGN_EXPIRE 控制（默认 30 分钟）。
    """
    from app.services.agent_export_service import AgentExportService

    export_service = AgentExportService(db)

    try:
        download_url, expired_at = await export_service.get_download_url(
            export_id, current_user.tenant_id or 0
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return APIResponse(
        code=0,
        data=ExportDownloadResponse(
            download_url=download_url,
            expired_at=expired_at.isoformat(),
        ).model_dump(),
        message="success",
    )
