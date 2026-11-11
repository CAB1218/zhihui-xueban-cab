"""
AI4EDU 课程梳理 API
任务1：用户输入课程 → 联网检索+LLM 梳理 → 学习内容与要求清单/必要联系/材料出处
支持 JSON / Markdown / Word 三格式导出
"""
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile
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
from app.services import import_service
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


# ---------------------------------------------------------------------------
# 文件导入（学生/教师上传课表、课程大纲）
# ---------------------------------------------------------------------------

_IMPORT_TEMPLATE_CSV = """课程名称,学科,学段年级,单元,学习内容,内容说明,要求,要求水平,认知水平,建议课时,教材出处
数据结构,计算机科学,大二,线性表,线性表的定义与基本操作,顺序表与链表的初始化、插入、删除,掌握线性表的抽象数据类型定义,掌握,understand,2,严蔚敏《数据结构》第2章
数据结构,计算机科学,大二,线性表,顺序表与链表的实现比较,从时间与空间维度比较两种存储结构,能结合场景选择存储结构,运用,analyze,2,严蔚敏《数据结构》第2章
数据结构,计算机科学,大二,栈与队列,栈的定义与表达式求值,中缀转后缀与求值流程,掌握栈在表达式求值中的应用,掌握,apply,2,严蔚敏《数据结构》第3章
"""

_IMPORT_FILE_TYPES = (".csv", ".xlsx", ".txt", ".md", ".json")


@router.get("/import/template", summary="下载课表/大纲导入模板")
async def import_template(
    current_user: User = Depends(get_current_user),
) -> Response:
    """CSV 模板（UTF-8 带 BOM，可直接用 Excel 打开编辑）"""
    from urllib.parse import quote

    return Response(
        content=_IMPORT_TEMPLATE_CSV.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote('课表大纲导入模板.csv', safe='')}"},
    )


@router.post("/import", summary="导入课表 / 课程大纲文件")
async def import_outline(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[CurriculumOutlineResponse]:
    """支持 .csv / .xlsx（按模板列整理）、.txt / .md（章节+条目文本）、
    .json（本系统导出的梳理成果），解析后直接生成一条可用的梳理记录。

    导入成果的「材料出处」会如实标注为上传文件，不冒充联网检索结果。
    """
    filename = file.filename or "outline.csv"
    lower = filename.lower()
    if not lower.endswith(_IMPORT_FILE_TYPES):
        raise AppException(code=400, message="仅支持 .csv / .xlsx / .txt / .md / .json 文件")
    data = await file.read()
    if len(data) > import_service.MAX_FILE_BYTES:
        raise AppException(code=400, message="文件超过 5MB 上限")
    if not data:
        raise AppException(code=400, message="文件为空")

    if lower.endswith(".json"):
        skeleton = import_service.parse_curriculum_json(data, filename)
    elif lower.endswith((".txt", ".md")):
        skeleton = import_service.parse_curriculum_text(data, filename)
    else:
        skeleton = import_service.parse_curriculum_table(data, filename)

    service = CurriculumService(db)
    record = await service.save_imported_outline(
        user_id=current_user.id,
        tenant_id=current_user.tenant_id or 0,
        filename=filename,
        skeleton=skeleton,
    )
    return APIResponse(data=_to_response(record), message="导入成功")
