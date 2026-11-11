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

from fastapi import APIRouter, Depends, File, Query, UploadFile
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


# ---------------------------------------------------------------------------
# 学情数据导入（学生/教师上传成绩、答题记录文件）
# ---------------------------------------------------------------------------

_IMPORT_TEMPLATE_CSV = """学生姓名,课程,知识点,记录类型,对错,得分,满分,耗时(秒),题目数,记录时间,来源
孙悦,数据结构,排序,测验,对,85,100,180,5,2026-01-08 09:30,第一章测验
孙悦,数据结构,图的遍历,作业,错,60,100,240,4,2026-01-09 15:00,课后作业1
李华,数据结构,栈与队列,考试,对,92,100,300,6,2026-01-10 10:00,期中考试
"""

_IMPORT_FILE_TYPES = (".csv", ".xlsx", ".txt")


@router.get("/import/template", summary="下载学情导入模板")
async def import_template(
    current_user: User = Depends(get_current_user),
) -> Response:
    """CSV 模板（UTF-8 带 BOM，可直接用 Excel 打开编辑）"""
    return Response(
        content=_IMPORT_TEMPLATE_CSV.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote('学情导入模板.csv')}"},
    )


@router.post("/import", summary="导入成绩 / 答题记录（csv / xlsx）")
async def import_records(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """学生可导入自己的练习/成绩记录；教师与管理员可为任意学生导入。

    校验失败的行不会入库，会在返回中列出行号与原因，修正后可重新导入。
    """
    from app.models.learning_record import LearningRecord
    from app.services import import_service

    filename = file.filename or "import.csv"
    if not filename.lower().endswith(_IMPORT_FILE_TYPES):
        raise AppException(code=400, message="仅支持 .csv / .xlsx 文件")
    data = await file.read()
    if len(data) > import_service.MAX_FILE_BYTES:
        raise AppException(code=400, message="文件超过 5MB 上限")
    if not data:
        raise AppException(code=400, message="文件为空")

    rows, bad_rows = import_service.parse_learning_record_rows(data, filename)

    tenant_id = current_user.tenant_id or 0
    is_staff = getattr(current_user, "role", "") in {"teacher", "admin", "super_admin"}

    # 学生只能导入自己的数据，教师/管理员按文件中的学生列匹配
    users = (
        (await db.execute(select(User).where(User.tenant_id == tenant_id))).scalars().all()
    )
    by_name: dict = {}
    for u in users:
        by_name.setdefault(u.nickname.strip(), u.id)
    by_id = {str(u.id): u.id for u in users}

    courses = (
        (await db.execute(select(Course).where(Course.tenant_id == tenant_id))).scalars().all()
    )
    course_by_name: dict = {}
    for c in courses:
        course_by_name.setdefault(c.name.strip(), c.id)
    course_by_id = {str(c.id): c.id for c in courses}

    new_records: list = []
    resolve_errors: list = list(bad_rows)
    for item in rows:
        if is_staff:
            key = item["student_key"].strip()
            sid = by_id.get(key) or by_name.get(key)
            if sid is None:
                resolve_errors.append(
                    {"row": item["row_no"], "reasons": [f"学生「{key}」在本租户中不存在"], "raw": json_loads_safe(item["raw"])}
                )
                continue
        else:
            sid = current_user.id

        ckey = (item["course_key"] or "").strip()
        cid = course_by_id.get(ckey) or course_by_name.get(ckey) if ckey else None
        if ckey and cid is None:
            resolve_errors.append(
                {"row": item["row_no"], "reasons": [f"课程「{ckey}」在本租户中不存在"], "raw": json_loads_safe(item["raw"])}
            )
            continue

        new_records.append(
            LearningRecord(
                tenant_id=tenant_id,
                student_id=sid,
                course_id=cid,
                knowledge_point=item["knowledge_point"],
                record_type=item["record_type"],
                source_ref=item["source_ref"],
                question_count=item["question_count"],
                is_correct=item["is_correct"],
                score=item["score"],
                max_score=item["max_score"],
                duration_seconds=item["duration_seconds"],
                recorded_at=item["recorded_at"],
                is_simulated=False,  # 如实标注：导入的是真实数据，与演示模拟数据区分
                raw_payload=item["raw"],
            )
        )

    if new_records:
        db.add_all(new_records)
        await db.commit()

    return APIResponse(
        code=0,
        data={
            "filename": filename,
            "total_rows": len(rows) + len(bad_rows),
            "imported": len(new_records),
            "failed": len(resolve_errors),
            "errors": resolve_errors[:50],
            "errors_truncated": len(resolve_errors) > 50,
        },
        message=f"成功导入 {len(new_records)} 条记录"
        + (f"，{len(resolve_errors)} 行未通过校验" if resolve_errors else ""),
    )


def json_loads_safe(text: str):
    import json as _json

    try:
        return _json.loads(text)
    except Exception:  # noqa: BLE001
        return {}
