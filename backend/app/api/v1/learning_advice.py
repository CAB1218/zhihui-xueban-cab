"""
AI4EDU 个性化学习建议 API（任务3：理解教学 — 个性化学习建议）

端点（挂载在 /learning-advice 下）：
    GET    /courses                    可选课程列表
    GET    /students                   有学情记录的学生（可按课程过滤）
    POST   /generate                   生成一份建议方案并落库
    GET    /plans                      历史方案列表（可按学生过滤）
    GET    /plans/{id}                 方案详情
    DELETE /plans/{id}                 删除方案
    GET    /plans/{id}/export          导出 Markdown
    POST   /students/import            导入学生名单（csv / xlsx）
    GET    /students/import/template   下载学生名单模板

权限：所有登录用户可用（学生可给自己生成，教师可为任意学生生成）
"""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import quote as _quote

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import hash_password
from app.dependencies import get_current_user, get_db
from app.models.course import Course
from app.models.learning_plan import LearningPlan
from app.models.user import User
from app.schemas.common import APIResponse
from app.services import import_service
from app.services.learning_advice_service import LearningAdviceService
from app.services.learning_analysis_service import LearningAnalysisService

router = APIRouter()

DEFAULT_STUDENT_PASSWORD = "student123"
_IMPORT_FILE_TYPES = (".csv", ".xlsx")


class GenerateRequest(BaseModel):
    student_id: int = Field(..., description="学生用户ID")
    course_id: Optional[int] = Field(None, description="课程ID，不传则按全部课程生成")
    duration_days: int = Field(7, ge=1, le=30, description="建议周期（天）")
    focus: Optional[str] = Field(None, max_length=200, description="教师指定的优先补强知识点")


def _tenant(user: User) -> int:
    return user.tenant_id or 0


async def _course_brief(db: AsyncSession, course_id: Optional[int]) -> Dict[str, Any]:
    if not course_id:
        return {"id": None, "name": "全部课程"}
    c = (await db.execute(select(Course).where(Course.id == course_id))).scalars().first()
    if c is None:
        raise AppException(code=404, message="课程不存在")
    return {"id": c.id, "name": c.name, "subject": c.subject, "grade": c.grade}


async def _student_brief(db: AsyncSession, student_id: int) -> Dict[str, Any]:
    u = (await db.execute(select(User).where(User.id == student_id))).scalars().first()
    if u is None:
        raise AppException(code=404, message="学生不存在")
    return {
        "id": u.id,
        "name": u.nickname,
        "grade": u.grade,
        "major": u.major,
        "school": u.school,
    }


@router.get("/courses", summary="可选课程列表")
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    rows = (
        await db.execute(
            select(Course).where(Course.tenant_id == _tenant(current_user)).order_by(Course.id)
        )
    ).scalars().all()
    return APIResponse(
        code=0,
        data=[{"id": c.id, "name": c.name, "subject": c.subject} for c in rows],
        message="success",
    )


@router.get("/students", summary="有学情记录的学生列表")
async def list_students(
    course_id: Optional[int] = Query(None, description="限定课程"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """按课程返回有记录的学生；没有记录的学生不会出现（建议生成页另有「全部学生」入口）"""
    analysis = LearningAnalysisService(db)
    records = await analysis.load_records(_tenant(current_user), course_id)

    by_student: Dict[int, list] = {}
    for r in records:
        by_student.setdefault(r.student_id, []).append(r)

    stmt_users = select(User).where(
        User.tenant_id == _tenant(current_user), User.role == "student"
    )
    if (current_user.role or "") == "student":
        # 学生只看自己，避免把全班的正确率暴露给学生
        stmt_users = stmt_users.where(User.id == current_user.id)
    users = (await db.execute(stmt_users)).scalars().all()
    umap = {u.id: u for u in users}

    out: List[Dict[str, Any]] = []
    for sid, recs in by_student.items():
        u = umap.get(sid)
        if u is None:
            continue
        judgeable = [r for r in recs if r.judgeable]
        acc = (
            round(sum(1 for r in judgeable if r.correct) / len(judgeable), 4)
            if judgeable
            else None
        )
        out.append(
            {
                "student_id": sid,
                "name": u.nickname,
                "grade": u.grade,
                "record_count": len(recs),
                "judgeable_count": len(judgeable),
                "accuracy": acc,
                "sufficient": len(judgeable) >= 3,
            }
        )
    # 证据不足的学生也保留在列表里，便于演示「信息不足时怎么给建议」
    for u in users:
        if u.id in by_student:
            continue
        out.append(
            {
                "student_id": u.id,
                "name": u.nickname,
                "grade": u.grade,
                "record_count": 0,
                "judgeable_count": 0,
                "accuracy": None,
                "sufficient": False,
            }
        )
    out.sort(key=lambda x: (x["record_count"] == 0, -(x["record_count"] or 0), x["name"]))
    return APIResponse(code=0, data=out, message="success")


@router.post("/generate", summary="生成个性化学习建议")
async def generate_plan(
    body: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """生成方案并落库；即使该学生没有任何记录，也会产出「补充观察」型方案，而不是直接报错"""
    tenant_id = _tenant(current_user)
    if (current_user.role or "") == "student" and body.student_id != current_user.id:
        raise AppException(code=403, message="学生只能为自己生成学习建议")
    student = await _student_brief(db, body.student_id)
    course = await _course_brief(db, body.course_id)

    analysis = LearningAnalysisService(db)
    cohort = await analysis.load_records(tenant_id, body.course_id)
    records = [r for r in cohort if r.student_id == body.student_id]

    service = LearningAdviceService(db)
    plan = await service.build_plan(
        tenant_id=tenant_id,
        student=student,
        course=course,
        records=records,
        cohort_records=cohort,
        duration_days=body.duration_days,
        focus=body.focus,
    )
    plan["plan_id"] = None

    row = LearningPlan(
        tenant_id=tenant_id,
        user_id=current_user.id,
        student_id=body.student_id,
        student_name=student["name"],
        course_id=course.get("id"),
        course_name=course.get("name"),
        title=f"{student['name']} · {course.get('name')} 个性化学习建议",
        duration_days=body.duration_days,
        focus=body.focus,
        plan_json=json.dumps(plan, ensure_ascii=False),
        source_json=json.dumps(
            {
                "outline": plan.get("outline"),
                "records_valid": plan["summary"].get("records_valid"),
                "attempts": plan["summary"].get("attempts"),
                "resources_checked": plan.get("resources_checked"),
                "generated_at": plan["generated_at"],
            },
            ensure_ascii=False,
        ),
        model_name=plan.get("engine"),
        status="completed",
    )
    db.add(row)
    await db.flush()

    plan["plan_id"] = row.id
    row.plan_json = json.dumps(plan, ensure_ascii=False)
    await db.flush()

    return APIResponse(code=0, data=plan, message="建议已生成")


@router.get("/plans", summary="历史方案列表")
async def list_plans(
    student_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    stmt = select(LearningPlan).where(LearningPlan.tenant_id == _tenant(current_user))
    if student_id:
        stmt = stmt.where(LearningPlan.student_id == student_id)
    if (current_user.role or "") == "student":
        stmt = stmt.where(LearningPlan.student_id == current_user.id)
    stmt = stmt.order_by(LearningPlan.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return APIResponse(
        code=0,
        data=[
            {
                "id": r.id,
                "student_id": r.student_id,
                "student_name": r.student_name,
                "course_id": r.course_id,
                "course_name": r.course_name,
                "title": r.title,
                "duration_days": r.duration_days,
                "focus": r.focus,
                "engine": r.model_name,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
        message="success",
    )


async def _load_plan(db: AsyncSession, plan_id: int, user: User) -> LearningPlan:
    row = (
        await db.execute(
            select(LearningPlan).where(
                LearningPlan.id == plan_id, LearningPlan.tenant_id == _tenant(user)
            )
        )
    ).scalars().first()
    if row is None:
        raise AppException(code=404, message="方案不存在")
    if (user.role or "") == "student" and row.student_id != user.id:
        raise AppException(code=403, message="只能查看自己的建议方案")
    return row


@router.get("/plans/{plan_id}", summary="方案详情")
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    row = await _load_plan(db, plan_id, current_user)
    try:
        data = json.loads(row.plan_json or "{}")
    except ValueError:
        raise AppException(code=500, message="方案数据损坏")
    data["plan_id"] = row.id
    return APIResponse(code=0, data=data, message="success")


@router.delete("/plans/{plan_id}", summary="删除方案")
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    row = await _load_plan(db, plan_id, current_user)
    await db.execute(delete(LearningPlan).where(LearningPlan.id == row.id))
    return APIResponse(code=0, data={"id": plan_id}, message="方案已删除")


@router.get("/plans/{plan_id}/export", summary="导出 Markdown")
async def export_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    row = await _load_plan(db, plan_id, current_user)
    plan = json.loads(row.plan_json or "{}")
    md = LearningAdviceService(db).render_markdown(plan)
    name = f"{row.student_name or '学生'}-{row.course_name or '课程'}-个性化学习建议.md"
    return Response(
        content=md.encode("utf-8-sig"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{_quote(name)}"},
    )


@router.get("/students/import/template", summary="下载学生名单导入模板")
async def students_template(current_user: User = Depends(get_current_user)) -> Response:
    return Response(
        content=import_service.students_template_csv(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{_quote('学生名单导入模板.csv')}"
        },
    )


@router.post("/students/import", summary="导入学生名单（csv / xlsx）")
async def import_students(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """姓名必填、邮箱选填：没有邮箱时自动生成占位邮箱（该学生暂不能登录，但可挂学情记录）。

    已存在的邮箱不会重复建号，计入「已存在跳过」；坏行不入库并返回行号与原因。
    """
    if (current_user.role or "") not in {"teacher", "admin", "super_admin"}:
        raise AppException(code=403, message="只有教师或管理员可以导入学生名单")

    filename = file.filename or "students.csv"
    if not filename.lower().endswith(_IMPORT_FILE_TYPES):
        raise AppException(code=400, message="仅支持 .csv / .xlsx 文件")
    data = await file.read()
    if not data:
        raise AppException(code=400, message="文件为空")
    if len(data) > import_service.MAX_FILE_BYTES:
        raise AppException(code=400, message="文件超过 5MB 上限")

    rows, errors = import_service.parse_student_rows(data, filename)
    tenant_id = _tenant(current_user)

    existing = (
        await db.execute(select(User.email).where(User.tenant_id == tenant_id))
    ).scalars().all()
    emails = {(e or "").lower() for e in existing}

    created: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    seq = 0
    for item in rows:
        email = item["email"]
        if email and email in emails:
            skipped.append(
                {
                    "row": item["row_no"],
                    "name": item["name"],
                    "reason": f"邮箱 {email} 已存在，跳过（如需更新请到用户管理修改）",
                }
            )
            continue
        if not email:
            seq += 1
            email = f"stu{datetime.utcnow().strftime('%y%m%d%H%M%S')}{seq}@student.local"
            while email in emails:
                seq += 1
                email = f"stu{datetime.utcnow().strftime('%y%m%d%H%M%S')}{seq}@student.local"
        user = User(
            tenant_id=tenant_id,
            email=email,
            nickname=item["name"],
            password_hash=hash_password(DEFAULT_STUDENT_PASSWORD),
            role="student",
            grade=item["grade"],
            major=item["major"],
            school=item["school"],
            onboarding_completed=True,
            is_active=True,
        )
        db.add(user)
        emails.add(email)
        created.append({"row": item["row_no"], "name": item["name"], "email": email})

    await db.flush()
    return APIResponse(
        code=0,
        data={
            "total": len(rows) + len(errors),
            "created": len(created),
            "skipped": len(skipped),
            "failed": len(errors),
            "created_rows": created,
            "skipped_rows": skipped,
            "errors": errors,
            "default_password": DEFAULT_STUDENT_PASSWORD if created else None,
        },
        message=f"导入完成：新增 {len(created)} 人，跳过 {len(skipped)} 人，{len(errors)} 行未通过校验",
    )
