"""
AI4EDU 学情分析 API
任务2：模拟学情数据的整理与质量检查 → 个体/群体学习情况摘要

端点：
    GET  /learning-analysis/overview            数据总览（含质量摘要）
    GET  /learning-analysis/quality             质量检查明细（缺失/异常/重复及处理方式）
    GET  /learning-analysis/students            有记录的学生列表
    GET  /learning-analysis/individual/{id}     个体摘要
    GET  /learning-analysis/group               群体摘要
    GET  /learning-analysis/export              导出 Markdown / Word
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.dependencies import get_current_user, get_db
from app.models.course import Course
from app.models.user import User
from app.schemas.common import APIResponse
from app.services.learning_analysis_service import LearningAnalysisService

router = APIRouter()


async def _course_dict(db: AsyncSession, course_id: Optional[int]) -> dict:
    if not course_id:
        return {}
    c = (
        await db.execute(select(Course).where(Course.id == course_id))
    ).scalars().first()
    if c is None:
        return {}
    return {
        "id": c.id,
        "name": c.name,
        "subject": c.subject,
        "grade": c.grade,
        "semester": c.semester,
    }


@router.get("/overview", summary="学情数据总览")
async def overview(
    course_id: Optional[int] = Query(None, description="课程ID，不传则统计全部"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """返回记录规模、覆盖学生数与质量概况，用于页面顶部卡片"""
    service = LearningAnalysisService(db)
    tenant_id = current_user.tenant_id or 0
    records = await service.load_records(tenant_id, course_id)
    quality = service.check_quality(records)

    students = {r.student_id for r in records}
    courses = {r.course_id for r in records if r.course_id}
    # 时间范围以「有效记录」为准：原始数据里可能混有未来时间等异常，不能直接展示
    dates = sorted({r.recorded_at.date() for r in quality.valid})

    by_type = {}
    for r in records:
        by_type[r.record_type] = by_type.get(r.record_type, 0) + 1

    judgeable = sum(1 for r in quality.valid if r.judgeable)
    correct = sum(1 for r in quality.valid if r.judgeable and r.correct)

    # 如实标注数据来源：模拟数据需在界面上明确说明，不能冒充真实教学数据
    from sqlalchemy import func

    from app.models.learning_record import LearningRecord

    simulated = (
        await db.execute(
            select(func.count())
            .select_from(LearningRecord)
            .where(
                LearningRecord.tenant_id == tenant_id,
                LearningRecord.is_simulated.is_(True),
                *([LearningRecord.course_id == course_id] if course_id else []),
            )
        )
    ).scalar() or 0

    return APIResponse(
        code=0,
        data={
            "course": await _course_dict(db, course_id),
            "records_total": quality.raw_count,
            "records_valid": quality.valid_count,
            "records_excluded": quality.raw_count - quality.valid_count,
            "judgeable": judgeable,
            "accuracy": round(correct / judgeable, 4) if judgeable else None,
            "students": len(students),
            "courses": len(courses),
            "date_from": dates[0].isoformat() if dates else None,
            "date_to": dates[-1].isoformat() if dates else None,
            "record_type_distribution": by_type,
            "quality_counts": quality.counts,
            "is_simulated": simulated >= quality.raw_count > 0,
            "simulated_count": simulated,
        },
        message="success",
    )


@router.get("/quality", summary="数据质量检查")
async def quality_check(
    course_id: Optional[int] = Query(None, description="课程ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """缺失 / 异常 / 重复三类问题，含处理方式与处理前后条数"""
    service = LearningAnalysisService(db)
    q = service.check_quality(await service.load_records(current_user.tenant_id or 0, course_id))
    return APIResponse(
        code=0,
        data={
            "raw_count": q.raw_count,
            "valid_count": q.valid_count,
            "removed_count": q.raw_count - q.valid_count,
            "counts": q.counts,
            "issues": q.issues,
            "steps": q.steps,
            "notes": q.notes,
        },
        message="success",
    )


@router.get("/students", summary="有学情记录的学生")
async def students(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    service = LearningAnalysisService(db)
    return APIResponse(
        code=0,
        data=await service.list_students(current_user.tenant_id or 0),
        message="success",
    )


@router.get("/individual/{student_id}", summary="个体学情摘要")
async def individual(
    student_id: int,
    course_id: Optional[int] = Query(None, description="限定课程"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    service = LearningAnalysisService(db)
    tenant_id = current_user.tenant_id or 0

    student = (
        await db.execute(select(User).where(User.id == student_id))
    ).scalars().first()
    if student is None:
        raise AppException(code=404, message="学生不存在")

    records = await service.load_records(tenant_id, course_id)
    records = [r for r in records if r.student_id == student_id]
    if not records:
        raise AppException(code=404, message="该学生暂无学情记录")

    course = await _course_dict(db, course_id)
    q = service.check_quality(records)
    data = service.individual_summary(
        records,
        student={
            "id": student.id,
            "name": student.nickname,
            "grade": student.grade,
            "major": student.major,
            "email": student.email,
        },
        quality=q,
        course_name=course.get("name"),
    )
    data["quality"] = {
        "raw_count": q.raw_count,
        "valid_count": q.valid_count,
        "counts": q.counts,
        "issues": q.issues,
    }
    return APIResponse(code=0, data=data, message="success")


@router.get("/group", summary="群体学情摘要")
async def group(
    course_id: Optional[int] = Query(None, description="课程ID，不传则跨课程统计"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    service = LearningAnalysisService(db)
    tenant_id = current_user.tenant_id or 0

    records = await service.load_records(tenant_id, course_id)
    if not records:
        raise AppException(code=404, message="暂无学情记录")

    roster = await service.list_students(tenant_id)
    students = {
        s["student_id"]: {"name": s["name"], "grade": s["grade"], "major": s["major"]}
        for s in roster
    }
    course = await _course_dict(db, course_id)
    q = service.check_quality(records)
    data = service.group_summary(records, course, students=students, quality=q)
    data["quality"] = {
        "raw_count": q.raw_count,
        "valid_count": q.valid_count,
        "counts": q.counts,
        "issues": q.issues,
        "steps": q.steps,
        "notes": q.notes,
    }
    return APIResponse(code=0, data=data, message="success")


@router.get("/export", summary="导出学情分析报告")
async def export(
    kind: str = Query("group", pattern="^(group|individual)$", description="group / individual"),
    course_id: Optional[int] = Query(None),
    student_id: Optional[int] = Query(None, description="kind=individual 时必填"),
    fmt: str = Query("md", alias="format", pattern="^(md|docx)$", description="md / docx"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    service = LearningAnalysisService(db)
    tenant_id = current_user.tenant_id or 0
    records = await service.load_records(tenant_id, course_id)
    if not records:
        raise AppException(code=404, message="暂无学情记录")

    course = await _course_dict(db, course_id)
    q = service.check_quality(records)

    if kind == "individual":
        if not student_id:
            raise AppException(code=400, message="导出个体报告需要指定 student_id")
        student = (
            await db.execute(select(User).where(User.id == student_id))
        ).scalars().first()
        if student is None:
            raise AppException(code=404, message="学生不存在")
        srecs = [r for r in records if r.student_id == student_id]
        if not srecs:
            raise AppException(code=404, message="该学生暂无学情记录")
        sq = service.check_quality(srecs)
        data = service.individual_summary(
            srecs,
            student={
                "id": student.id,
                "name": student.nickname,
                "grade": student.grade,
                "major": student.major,
            },
            quality=sq,
            course_name=course.get("name"),
        )
        q_use = sq
        title = f"{student.nickname}_学情分析"
    else:
        roster = await service.list_students(tenant_id)
        students = {s["student_id"]: {"name": s["name"]} for s in roster}
        data = service.group_summary(records, course, students=students, quality=q)
        q_use = q
        title = f"{course.get('name') or '班级'}_学情分析"

    if fmt == "docx":
        body = service.render_docx(kind, data, q_use)
        return Response(
            content=body,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{_quote(title)}.docx"
            },
        )

    md = service.render_markdown(kind, data, q_use)
    return Response(
        content=md.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(title)}.md"},
    )


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")
