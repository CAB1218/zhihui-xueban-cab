"""
智慧学伴 教师工作台 API
提供教案管理、作业批改、学情分析等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.common import APIResponse, PaginationParams
from app.services.teacher_service import TeacherService

router = APIRouter()


class LessonPlanCreate(BaseModel):
    """创建教案请求"""

    course_id: Optional[int] = Field(None, description="课程ID")
    course_name: Optional[str] = Field(None, description="课程名称；未提供课程ID时用于关联或创建课程")
    title: str = Field(..., description="教案标题", min_length=1, max_length=300)
    objectives: Optional[list[str]] = Field(None, description="教学目标")
    content: Optional[str] = Field(None, description="教案内容")
    materials: Optional[list[str]] = Field(None, description="教学材料")
    duration_minutes: int = Field(45, description="时长(分钟)")
    ai_generated: bool = Field(False, description="是否由AI生成")


class LessonPlanUpdate(BaseModel):
    """更新教案请求"""

    title: Optional[str] = Field(None, description="教案标题")
    objectives: Optional[list[str]] = Field(None, description="教学目标")
    content: Optional[str] = Field(None, description="教案内容")
    materials: Optional[list[str]] = Field(None, description="教学材料")
    duration_minutes: Optional[int] = Field(None, description="时长(分钟)")
    status: Optional[str] = Field(None, description="状态: draft/published/archived")


class LessonPlanPreviewRequest(BaseModel):
    """AI教案预览请求。"""

    course_name: str = Field(..., min_length=1, max_length=200)
    objectives: Optional[str] = None
    knowledge_points: list[str] = Field(default_factory=list)
    duration: int = Field(45, ge=10, le=300)
    student_level: str = Field("intermediate", max_length=50)


@router.get("/dashboard", summary="教师仪表盘")
async def teacher_dashboard(
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取教师工作台仪表盘数据"""
    service = TeacherService(db)
    result = await service.get_dashboard(
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/lesson-plans", summary="获取教案列表")
async def list_lesson_plans(
    pagination: PaginationParams = Depends(),
    course_id: Optional[int] = Query(None, description="课程ID筛选"),
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取教案列表"""
    service = TeacherService(db)
    result = await service.list_lesson_plans(
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
        pagination=pagination,
        course_id=course_id,
    )
    return APIResponse(code=0, data=result.model_dump(), message="success")


@router.get("/courses", summary="获取教师课程列表")
async def list_teacher_courses(
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取当前教师维护的真实课程，供工作台和班级诊断使用。"""
    service = TeacherService(db)
    result = await service.list_courses(
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/lesson-plans", summary="创建教案")
async def create_lesson_plan(
    plan_data: LessonPlanCreate,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """创建新教案（支持AI辅助生成）"""
    service = TeacherService(db)
    course_id = plan_data.course_id
    if course_id is None:
        if not plan_data.course_name or not plan_data.course_name.strip():
            raise HTTPException(status_code=400, detail="课程ID和课程名称至少需要提供一项")
        course_id = await service.get_or_create_course(
            tenant_id=current_user.tenant_id or 0,
            teacher_id=current_user.id,
            course_name=plan_data.course_name.strip(),
        )
    result = await service.create_lesson_plan(
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
        course_id=course_id,
        title=plan_data.title,
        objectives=plan_data.objectives,
        content=plan_data.content,
        materials=plan_data.materials,
        duration_minutes=plan_data.duration_minutes,
        ai_generated=plan_data.ai_generated,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/lesson-plans/generate-preview", summary="AI生成教案预览")
async def generate_lesson_plan_preview(
    request: LessonPlanPreviewRequest,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """根据教师输入生成尚未保存的结构化教案预览。"""
    service = TeacherService(db)
    result = await service.generate_lesson_plan_preview(
        course_name=request.course_name,
        objectives=request.objectives,
        knowledge_points=request.knowledge_points,
        duration=request.duration,
        student_level=request.student_level,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id or 0,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/lesson-plans/{plan_id}", summary="获取教案详情")
async def get_lesson_plan(
    plan_id: int,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取教案详情"""
    service = TeacherService(db)
    result = await service.get_lesson_plan(
        plan_id=plan_id,
        tenant_id=current_user.tenant_id or 0,
    )
    if not result:
        raise HTTPException(status_code=404, detail="教案不存在")
    return APIResponse(code=0, data=result, message="success")


@router.put("/lesson-plans/{plan_id}", summary="更新教案")
async def update_lesson_plan(
    plan_id: int,
    plan_data: LessonPlanUpdate,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新教案"""
    service = TeacherService(db)
    result = await service.update_lesson_plan(
        plan_id=plan_id,
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
        title=plan_data.title,
        objectives=plan_data.objectives,
        content=plan_data.content,
        materials=plan_data.materials,
        duration_minutes=plan_data.duration_minutes,
        status=plan_data.status,
        bypass_owner_check=current_user.role == "super_admin",
    )
    if not result:
        raise HTTPException(status_code=404, detail="教案不存在或无权修改")
    return APIResponse(code=0, data=result, message="success")


@router.delete("/lesson-plans/{plan_id}", summary="删除教案")
async def delete_lesson_plan(
    plan_id: int,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """删除教案"""
    service = TeacherService(db)
    success = await service.delete_lesson_plan(
        plan_id=plan_id,
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
        bypass_owner_check=current_user.role == "super_admin",
    )
    if not success:
        raise HTTPException(status_code=404, detail="教案不存在")
    return APIResponse(code=0, data=None, message="教案已删除")


@router.post("/lesson-plans/{plan_id}/ai-generate", summary="AI生成教案")
async def ai_generate_lesson_plan(
    plan_id: int,
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """使用AI根据课程信息生成教案"""
    service = TeacherService(db)
    result = await service.ai_generate_lesson_plan(
        plan_id=plan_id,
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/students", summary="获取学生列表")
async def list_students(
    course_id: Optional[int] = Query(None, description="课程ID筛选"),
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取教师所教学生列表"""
    service = TeacherService(db)
    result = await service.list_students(
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
        course_id=course_id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/analytics", summary="学情分析")
async def learning_analytics(
    course_id: Optional[int] = Query(None, description="课程ID"),
    time_range: Optional[str] = Query("week", description="时间范围: day/week/month"),
    current_user: User = Depends(require_role(["teacher", "admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取学情分析数据"""
    service = TeacherService(db)
    result = await service.get_learning_analytics(
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
        course_id=course_id,
        time_range=time_range or "week",
    )
    return APIResponse(code=0, data=result, message="success")
