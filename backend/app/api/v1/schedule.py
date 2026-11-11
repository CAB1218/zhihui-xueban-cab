"""
AI4EDU 个人课表 API（场景仪表盘「导入课表」）

端点：
    GET    /dashboard/schedule/today      某天课程（默认今天，含进行中/已结束状态）
    GET    /dashboard/schedule/week       整周课表（按周一~周日分组）
    POST   /dashboard/schedule/import     导入课表（csv / xlsx，覆盖或追加）
    GET    /dashboard/schedule/template   下载导入模板
    DELETE /dashboard/schedule            清空我的课表

说明：
- 课表属于「个人」数据，读写都只针对当前登录用户自己的课表
- 导入逐行校验，坏行不入库并回传行号与原因，修好后可重复导入
"""
import logging
from datetime import date as date_cls
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.services import import_service
from app.services.schedule_service import ScheduleService

logger = logging.getLogger(__name__)

router = APIRouter()

_ALLOWED_TYPES = (".csv", ".xlsx")


def _tenant_of(user: User) -> int:
    tenant_id = getattr(user, "tenant_id", None)
    if not tenant_id:
        raise AppException(code=400, message="当前账号未归属任何租户，无法保存课表")
    return tenant_id


@router.get("/dashboard/schedule/today", summary="某天课程（默认今天）")
async def get_today_schedule(
    day: Optional[str] = Query(None, description="日期 YYYY-MM-DD，默认今天"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    target = None
    if day:
        try:
            target = date_cls.fromisoformat(day)
        except ValueError:
            raise AppException(code=400, message="日期格式应为 YYYY-MM-DD")
    data = await ScheduleService.list_day(db, current_user.id, target)
    return APIResponse(code=0, data=data)


@router.get("/dashboard/schedule/week", summary="整周课表")
async def get_week_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    data = await ScheduleService.list_week(db, current_user.id)
    return APIResponse(code=0, data=data)


@router.get("/dashboard/schedule/template", summary="下载课表导入模板")
async def schedule_template(
    current_user: User = Depends(get_current_user),
) -> Response:
    """CSV 模板（UTF-8 带 BOM，Excel 直接打开不乱码）"""
    return Response(
        content=import_service.schedule_template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('课表导入模板.csv')}"
        },
    )


@router.post("/dashboard/schedule/import", summary="导入课表（csv / xlsx）")
async def import_schedule(
    file: UploadFile = File(...),
    mode: str = Form("replace", description="replace=覆盖整份课表；append=追加"),
    dry_run: bool = Form(False, description="true=只校验不写库，用于导入前预览"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    filename = file.filename or "schedule.csv"
    if not filename.lower().endswith(_ALLOWED_TYPES):
        raise AppException(code=400, message="仅支持 .csv / .xlsx 文件")
    if mode not in ("replace", "append"):
        raise AppException(code=400, message="mode 只能是 replace 或 append")

    data = await file.read()
    if not data:
        raise AppException(code=400, message="文件为空")
    if len(data) > import_service.MAX_FILE_BYTES:
        raise AppException(code=400, message="文件超过 5MB 上限")

    rows, bad_rows = import_service.parse_schedule_rows(data, filename)
    if not rows and bad_rows:
        # 全部行都不合法：直接把原因回给用户，避免「导入 0 条」的黑盒体验
        return APIResponse(
            code=0,
            data={
                "filename": filename,
                "mode": mode,
                "total_rows": len(bad_rows),
                "imported": 0,
                "skipped": 0,
                "failed": len(bad_rows),
                "errors": bad_rows[:50],
                "errors_truncated": len(bad_rows) > 50,
            },
            message="没有可导入的有效行，请按提示修正后重试",
        )

    if dry_run:
        # 只校验不写库：让前端在「覆盖原课表」前先看到会有多少行失败
        return APIResponse(
            code=0,
            data={
                "filename": filename,
                "mode": mode,
                "dry_run": True,
                "total_rows": len(rows) + len(bad_rows),
                "imported": 0,
                "skipped": 0,
                "valid": len(rows),
                "failed": len(bad_rows),
                "errors": bad_rows[:50],
                "errors_truncated": len(bad_rows) > 50,
            },
            message=(
                f"校验通过 {len(rows)} 条"
                + (f"，{len(bad_rows)} 行需修正" if bad_rows else "")
            ),
        )

    tenant_id = _tenant_of(current_user)
    added = await ScheduleService.import_rows(
        db, tenant_id, current_user.id, rows, filename, mode=mode
    )
    skipped = len(rows) - added
    today = await ScheduleService.list_day(db, current_user.id)

    message = f"成功导入 {added} 条课表"
    if skipped:
        message += f"，{skipped} 条已存在被跳过"
    if bad_rows:
        message += f"，{len(bad_rows)} 行未通过校验"

    return APIResponse(
        code=0,
        data={
            "filename": filename,
            "mode": mode,
            "dry_run": False,
            "total_rows": len(rows) + len(bad_rows),
            "imported": added,
            "skipped": skipped,
            "failed": len(bad_rows),
            "errors": bad_rows[:50],
            "errors_truncated": len(bad_rows) > 50,
            "today_count": today["count"],
        },
        message=message,
    )


@router.delete("/dashboard/schedule", summary="清空我的课表")
async def clear_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    deleted = await ScheduleService.clear(db, current_user.id)
    return APIResponse(
        code=0,
        data={"deleted": deleted},
        message=f"已清空 {deleted} 条课表" if deleted else "课表本来就是空的",
    )
