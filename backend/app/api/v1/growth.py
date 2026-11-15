"""
智慧学伴 学生成长档案 API
评价 CRUD、时间线、仪表盘端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db, require_role
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.growth import (
    EvaluationCreate,
    EvaluationResponse,
    EvaluationUpdate,
    GrowthDashboard,
    TimelineItem,
)
from app.services.growth_service import GrowthService

router = APIRouter()


# ---------------------------------------------------------------------------
# 评价 CRUD
# ---------------------------------------------------------------------------

@router.post("/evaluations", summary="创建学生评价")
async def create_evaluation(
    data: EvaluationCreate,
    current_user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvaluationResponse]:
    """教师/管理员创建学生评价"""
    service = GrowthService(db)
    result = await service.create_evaluation(
        teacher_id=current_user.id,
        tenant_id=current_user.tenant_id or 0,
        data=data,
    )
    return APIResponse(data=result, message="success")


@router.get("/evaluations", summary="获取学生评价列表")
async def list_evaluations(
    student_id: int = Query(..., description="学生用户ID"),
    course_id: Optional[int] = Query(None, description="课程ID筛选"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PaginatedResponse[EvaluationResponse]]:
    """教师/管理员获取学生评价列表"""
    service = GrowthService(db)
    items, total = await service.list_evaluations(
        student_id=student_id,
        course_id=course_id,
        page=page,
        page_size=page_size,
    )
    return APIResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="success",
    )


@router.get("/evaluations/{evaluation_id}", summary="获取评价详情")
async def get_evaluation(
    evaluation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvaluationResponse]:
    """获取评价详情"""
    service = GrowthService(db)
    result = await service.get_evaluation(evaluation_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评价不存在")
    return APIResponse(data=result, message="success")


@router.put("/evaluations/{evaluation_id}", summary="更新评价")
async def update_evaluation(
    evaluation_id: int,
    data: EvaluationUpdate,
    current_user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[EvaluationResponse]:
    """更新评价（仅限评价作者）"""
    service = GrowthService(db)
    result = await service.update_evaluation(
        evaluation_id=evaluation_id,
        teacher_id=current_user.id,
        data=data,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="评价不存在或无权修改",
        )
    return APIResponse(data=result, message="success")


@router.delete("/evaluations/{evaluation_id}", summary="删除评价")
async def delete_evaluation(
    evaluation_id: int,
    current_user: User = Depends(require_role(["teacher", "admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[None]:
    """删除评价（仅限评价作者）"""
    service = GrowthService(db)
    success = await service.delete_evaluation(
        evaluation_id=evaluation_id,
        teacher_id=current_user.id,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="评价不存在或无权删除",
        )
    return APIResponse(data=None, message="评价已删除")


# ---------------------------------------------------------------------------
# 时间线
# ---------------------------------------------------------------------------

@router.get("/timeline", summary="获取学生成长时间线")
async def get_timeline(
    student_id: int = Query(..., description="学生用户ID"),
    source: Optional[str] = Query(
        None,
        description="数据源筛选: agent/diagnosis/note/flashcard/evaluation/course/resource/classroom",
    ),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[PaginatedResponse[TimelineItem]]:
    """获取学生成长时间线，学生只能查看自己的"""
    # 权限检查：学生只能查看自己的时间线
    if current_user.role == "student" and student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能查看自己的成长时间线",
        )

    service = GrowthService(db)
    items, total = await service.get_timeline(
        student_id=student_id,
        source=source,
        page=page,
        page_size=page_size,
    )
    return APIResponse(
        data=PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        ),
        message="success",
    )


# ---------------------------------------------------------------------------
# 仪表盘
# ---------------------------------------------------------------------------

@router.get("/dashboard", summary="获取成长仪表盘")
async def get_dashboard(
    student_id: Optional[int] = Query(None, description="学生用户ID(学生不传则默认查自己)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse[GrowthDashboard]:
    """获取学生成长仪表盘数据"""
    # 确定查询的学生 ID
    target_student_id = student_id
    if target_student_id is None:
        target_student_id = current_user.id
    else:
        # 权限检查：学生只能查看自己的仪表盘
        if current_user.role == "student" and target_student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能查看自己的成长仪表盘",
            )

    service = GrowthService(db)
    result = await service.get_dashboard(student_id=target_student_id)
    return APIResponse(data=result, message="success")
