"""
AI4EDU 个人课表服务

职责：
- 从导入文件落库（覆盖 / 追加两种模式）
- 按「今天」或「整周」读取课表，并把条目转成前端需要的结构
- 结合当前时间计算课程状态（进行中 / 已结束 / 未开始）

课表按「星期 + 起止时间」存储，不绑定具体日期，天然支持整学期循环课表。
"""
import logging
from datetime import date as date_cls
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course_schedule import CourseSchedule

logger = logging.getLogger(__name__)

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def weekday_of(day: Optional[date_cls] = None) -> int:
    """返回 ISO 星期（1=周一 … 7=周日）"""
    return (day or date_cls.today()).isoweekday()


def weekday_label(weekday: int) -> str:
    return WEEKDAY_LABELS[weekday - 1] if 1 <= weekday <= 7 else ""


def _status(start_time: str, end_time: str, now: datetime) -> str:
    """根据当前时刻判断课程状态，返回 ongoing / ended / upcoming"""
    current = now.strftime("%H:%M")
    if current < start_time:
        return "upcoming"
    if current > end_time:
        return "ended"
    return "ongoing"


def to_item(row: CourseSchedule, now: Optional[datetime] = None) -> Dict[str, Any]:
    """ORM 行 → 前端课表条目（含运行时状态）"""
    now = now or datetime.now()
    return {
        "id": row.id,
        "name": row.course_name,
        "weekday": row.weekday,
        "weekday_label": weekday_label(row.weekday),
        "start_time": row.start_time,
        "end_time": row.end_time,
        "location": row.location or "",
        "teacher": row.teacher or "",
        "weeks": row.weeks or "",
        "note": row.note or "",
        "status": _status(row.start_time, row.end_time, now),
        "source_file": row.source_file or "",
    }


class ScheduleService:
    """个人课表读写"""

    @staticmethod
    async def list_rows(db: AsyncSession, user_id: int) -> List[CourseSchedule]:
        result = await db.execute(
            select(CourseSchedule)
            .where(CourseSchedule.user_id == user_id)
            .order_by(CourseSchedule.weekday, CourseSchedule.start_time)
        )
        return list(result.scalars().all())

    @staticmethod
    async def list_day(
        db: AsyncSession, user_id: int, day: Optional[date_cls] = None
    ) -> Dict[str, Any]:
        """某一天的课程（默认今天）"""
        target = day or date_cls.today()
        weekday = weekday_of(target)
        rows = [r for r in await ScheduleService.list_rows(db, user_id) if r.weekday == weekday]
        now = datetime.now()
        items = [to_item(r, now) for r in rows]
        return {
            "date": target.isoformat(),
            "weekday": weekday,
            "weekday_label": weekday_label(weekday),
            "items": items,
            "count": len(items),
            "source": "imported" if rows else "empty",
            "updated_at": max((r.updated_at.isoformat() for r in rows), default=None),
        }

    @staticmethod
    async def list_week(db: AsyncSession, user_id: int) -> Dict[str, Any]:
        """整周课表，按 周一~周日 分组"""
        rows = await ScheduleService.list_rows(db, user_id)
        now = datetime.now()
        today_weekday = weekday_of()
        days: List[Dict[str, Any]] = []
        for wd in range(1, 8):
            day_items = [to_item(r, now) for r in rows if r.weekday == wd]
            days.append(
                {
                    "weekday": wd,
                    "label": weekday_label(wd),
                    "is_today": wd == today_weekday,
                    "count": len(day_items),
                    "items": day_items,
                }
            )
        return {
            "days": days,
            "total": len(rows),
            "source_file": next((r.source_file for r in rows if r.source_file), ""),
            "updated_at": max((r.updated_at.isoformat() for r in rows), default=None),
        }

    @staticmethod
    async def import_rows(
        db: AsyncSession,
        tenant_id: int,
        user_id: int,
        items: List[Dict[str, Any]],
        filename: str,
        mode: str = "replace",
    ) -> int:
        """写入课表：mode=replace 覆盖整份课表；mode=append 追加（同日同课同时段自动跳过）"""
        existing = await ScheduleService.list_rows(db, user_id)
        if mode == "replace":
            await db.execute(delete(CourseSchedule).where(CourseSchedule.user_id == user_id))
            existing = []

        seen = {(r.weekday, r.course_name, r.start_time) for r in existing}
        added = 0
        for item in items:
            key = (item["weekday"], item["course_name"], item["start_time"])
            if key in seen:
                continue
            seen.add(key)
            db.add(
                CourseSchedule(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    course_name=item["course_name"],
                    teacher=item["teacher"],
                    location=item["location"],
                    weekday=item["weekday"],
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    weeks=item["weeks"],
                    note=item["note"],
                    source_file=filename[:200],
                )
            )
            added += 1

        await db.commit()
        logger.info("课表导入完成 user=%s mode=%s added=%s", user_id, mode, added)
        return added

    @staticmethod
    async def clear(db: AsyncSession, user_id: int) -> int:
        """清空当前用户课表，返回删除条数"""
        rows = await ScheduleService.list_rows(db, user_id)
        if rows:
            await db.execute(delete(CourseSchedule).where(CourseSchedule.user_id == user_id))
            await db.commit()
        return len(rows)
