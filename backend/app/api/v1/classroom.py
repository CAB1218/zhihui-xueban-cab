"""
智慧学伴 课堂记录 API 端点
板书/录播上传 → MinIO 存储 → Celery 异步 OCR/ASR 提取

端点:
- POST   /agents/classroom-records        上传板书/录播文件
- GET    /agents/classroom-records        分页列表
- GET    /agents/classroom-records/{id}   获取详情
- DELETE /agents/classroom-records/{id}   删除记录
- POST   /agents/classroom-records/{id}/reprocess  重新处理
"""
import json
import logging
import uuid
from datetime import datetime
from io import BytesIO
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, get_db
from app.models.teacher_method import ClassroomRecord
from app.models.user import User
from app.schemas.classroom import ClassroomRecordResponse
from app.schemas.common import APIResponse, PaginatedResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# 允许的文件类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "audio/mpeg", "audio/wav", "audio/x-m4a"}
MAX_FILE_SIZE = settings.EXPORT_MAX_FILE_SIZE  # 100MB


def _get_minio_client():
    """获取 MinIO 客户端（复用 resource_service 模式）"""
    from minio import Minio

    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    # 确保 resources bucket 存在
    bucket = settings.MINIO_BUCKET
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
    return client


async def _upload_to_minio(file_data: bytes, file_key: str, content_type: str) -> str:
    """上传文件到 MinIO，返回 file_key

    Args:
        file_data: 文件二进制数据
        file_key: 存储 Key
        content_type: MIME 类型

    Returns:
        MinIO 中的 file_key
    """
    client = _get_minio_client()
    client.put_object(
        settings.MINIO_BUCKET,
        file_key,
        BytesIO(file_data),
        length=len(file_data),
        content_type=content_type,
    )
    return file_key


@router.post("", summary="上传板书/录播文件")
async def create_classroom_record(
    record_type: str = Form(..., description="类型: board_image/video_record"),
    classroom_id: Optional[int] = Form(None, description="课堂ID"),
    course_id: Optional[int] = Form(None, description="课程ID"),
    file: UploadFile = File(..., description="板书图片或录播视频文件"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """上传板书图片或录播视频，创建课堂记录并异步处理

    流程:
    1. 校验文件类型和大小（≤100MB）
    2. 上传到 MinIO
    3. 创建 ClassroomRecord（status=pending）
    4. 根据 record_type 触发对应 Celery 任务
    """
    # 校验文件类型
    content_type = file.content_type or ""
    if record_type == "board_image":
        if content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"板书图片仅支持 JPG/PNG/WebP，当前: {content_type}",
            )
    elif record_type == "video_record":
        if content_type not in ALLOWED_VIDEO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"录播文件仅支持 MP4/MOV/MP3/WAV/M4A，当前: {content_type}",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"record_type 必须为 board_image 或 video_record，当前: {record_type}",
        )

    # 读取文件内容并校验大小
    file_data = await file.read()
    if len(file_data) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制（≤{MAX_FILE_SIZE // 1024 // 1024}MB）",
        )

    # 上传到 MinIO
    file_ext = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else "bin"
    file_key = f"classroom/{current_user.tenant_id or 0}/{uuid.uuid4().hex}.{file_ext}"

    try:
        await _upload_to_minio(file_data, file_key, content_type)
    except Exception as e:
        logger.error("MinIO 上传失败: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"文件上传失败: {str(e)}",
        )

    # 创建 ClassroomRecord
    record = ClassroomRecord(
        tenant_id=current_user.tenant_id or 0,
        classroom_id=classroom_id or 0,
        course_id=course_id or 0,
        record_type=record_type,
        status="pending",
        file_url=file_key,
    )
    db.add(record)
    await db.flush()

    record_id = record.id

    # 触发 Celery 任务
    try:
        from app.tasks.extraction_tasks import process_board_ocr, process_video_asr

        if record_type == "board_image":
            process_board_ocr.delay(record_id)
        else:
            process_video_asr.delay(record_id)
    except Exception as e:
        logger.warning("Celery 任务触发失败（不影响记录创建）: %s", e)

    return APIResponse(
        code=0,
        data={
            "id": record_id,
            "record_type": record_type,
            "status": "pending",
            "file_url": file_key,
            "message": "已提交处理，请稍后查看状态",
        },
        message="success",
    )


@router.get("", summary="获取课堂记录列表")
async def list_classroom_records(
    classroom_id: Optional[int] = None,
    course_id: Optional[int] = None,
    record_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """分页获取课堂记录列表，支持 classroom_id/course_id/status 筛选"""
    conditions = [ClassroomRecord.tenant_id == (current_user.tenant_id or 0)]

    if classroom_id is not None:
        conditions.append(ClassroomRecord.classroom_id == classroom_id)
    if course_id is not None:
        conditions.append(ClassroomRecord.course_id == course_id)
    if record_type:
        conditions.append(ClassroomRecord.record_type == record_type)
    if status_filter:
        conditions.append(ClassroomRecord.status == status_filter)

    # 总数
    count_stmt = select(func.count(ClassroomRecord.id)).where(and_(*conditions))
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # 数据
    offset = (page - 1) * page_size
    stmt = (
        select(ClassroomRecord)
        .where(and_(*conditions))
        .order_by(desc(ClassroomRecord.created_at))
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    items = [_record_to_dict(r) for r in records]

    return APIResponse(
        code=0,
        data=PaginatedResponse(
            items=items, total=total, page=page, page_size=page_size
        ),
        message="success",
    )


@router.get("/{record_id}", summary="获取课堂记录详情")
async def get_classroom_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取课堂记录详情（含 transcript/segments）"""
    record = await _get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    return APIResponse(
        code=0,
        data=_record_to_dict(record),
        message="success",
    )


@router.delete("/{record_id}", summary="删除课堂记录")
async def delete_classroom_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """删除课堂记录"""
    record = await _get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    await db.delete(record)
    await db.flush()

    return APIResponse(code=0, data=None, message="记录已删除")


@router.post("/{record_id}/reprocess", summary="重新处理失败的记录")
async def reprocess_record(
    record_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """重新触发 OCR/ASR 处理"""
    record = await _get_record(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    # 重置状态
    record.status = "pending"
    record.error_msg = None
    await db.flush()

    # 重新触发 Celery 任务
    try:
        from app.tasks.extraction_tasks import process_board_ocr, process_video_asr

        if record.record_type == "board_image":
            process_board_ocr.delay(record_id)
        else:
            process_video_asr.delay(record_id)
    except Exception as e:
        logger.warning("Celery 任务触发失败: %s", e)

    return APIResponse(
        code=0,
        data={"id": record_id, "status": "pending", "message": "已重新提交处理"},
        message="success",
    )


# ============ 辅助函数 ============

async def _get_record(db: AsyncSession, record_id: int) -> Optional[ClassroomRecord]:
    """查询课堂记录"""
    stmt = select(ClassroomRecord).where(ClassroomRecord.id == record_id)
    result = await db.execute(stmt)
    return result.scalars().first()


def _record_to_dict(record: ClassroomRecord) -> dict:
    """将 ClassroomRecord 转为响应字典"""
    return {
        "id": record.id,
        "classroom_id": record.classroom_id,
        "course_id": record.course_id,
        "record_type": record.record_type,
        "status": record.status,
        "transcript": record.transcript,
        "segments": json.loads(record.segments) if record.segments else None,
        "knowledge_points": json.loads(record.knowledge_points) if record.knowledge_points else None,
        "provider": record.provider,
        "error_msg": record.error_msg,
        "file_url": record.file_url,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }
