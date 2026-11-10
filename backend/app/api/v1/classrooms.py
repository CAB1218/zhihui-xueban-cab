"""
AI4Edu 课堂互动 API
提供课堂创建、实时互动、举手、投票等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.classroom import (
    ClassroomCreate,
    ClassroomResponse,
    DanmakuMessage,
    JoinByCodeRequest,
    JoinClassroomRequest,
    PollCreate,
    PollResult,
    PollVote,
    RaiseHandRequest,
)
from app.schemas.common import APIResponse
from app.services.classroom_service import ClassroomService

router = APIRouter()


@router.post("/", summary="创建课堂")
async def create_classroom(
    classroom_data: ClassroomCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """创建新的课堂互动"""
    if current_user.role not in ("teacher", "admin", "super_admin"):
        raise HTTPException(status_code=403, detail="只有教师可以创建课堂")

    service = ClassroomService(db)
    result = await service.create_classroom(
        tenant_id=current_user.tenant_id or 0,
        teacher_id=current_user.id,
        course_id=classroom_data.course_id,
        title=classroom_data.title,
        description=classroom_data.description,
        max_participants=classroom_data.max_participants,
        settings=classroom_data.settings,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/", summary="我的课堂列表")
async def list_my_classrooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """教师返回自己创建的课堂，学生返回已加入的课堂"""
    service = ClassroomService(db)
    items = await service.list_classrooms(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        role=current_user.role,
    )
    return APIResponse(code=0, data=items, message="success")


@router.post("/join-by-code", summary="通过加入码加入课堂")
async def join_by_code(
    join_data: JoinByCodeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """学生输入 6 位加入码进入课堂"""
    service = ClassroomService(db)
    classroom = await service.join_by_code(
        access_code=join_data.access_code,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=classroom, message="success")


@router.get("/{classroom_id}", summary="获取课堂详情")
async def get_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取课堂详情"""
    service = ClassroomService(db)
    result = await service.get_classroom(
        classroom_id=classroom_id,
        tenant_id=current_user.tenant_id or 0,
    )
    if not result:
        raise HTTPException(status_code=404, detail="课堂不存在")
    return APIResponse(code=0, data=result, message="success")


@router.get("/{classroom_id}/participants", summary="课堂参与者列表")
async def list_participants(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取课堂参与者（含举手状态）"""
    service = ClassroomService(db)
    items = await service.list_participants(classroom_id)
    return APIResponse(code=0, data=items, message="success")


@router.get("/{classroom_id}/polls", summary="课堂投票列表")
async def list_polls(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取课堂全部投票及票数"""
    service = ClassroomService(db)
    items = await service.list_polls(classroom_id)
    return APIResponse(code=0, data=items, message="success")


@router.post("/{classroom_id}/join", summary="加入课堂")
async def join_classroom(
    classroom_id: int,
    join_data: Optional[JoinClassroomRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """学生加入课堂"""
    service = ClassroomService(db)
    await service.join_classroom(
        classroom_id=classroom_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        access_code=join_data.access_code if join_data else None,
    )
    # 返回完整的课堂信息（前端需要 id/status 才能继续举手、投票）
    classroom = await service.get_classroom(classroom_id, current_user.tenant_id or 0)
    return APIResponse(code=0, data=classroom, message="success")


@router.post("/{classroom_id}/leave", summary="离开课堂")
async def leave_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """学生离开课堂"""
    service = ClassroomService(db)
    success = await service.leave_classroom(
        classroom_id=classroom_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(status_code=400, detail="离开课堂失败")
    return APIResponse(code=0, data=None, message="已离开课堂")


@router.post("/{classroom_id}/raise-hand", summary="举手")
async def raise_hand(
    classroom_id: int,
    hand_data: RaiseHandRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """学生举手"""
    service = ClassroomService(db)
    success = await service.raise_hand(
        classroom_id=classroom_id,
        user_id=current_user.id,
        raised=hand_data.raised,
    )
    if not success:
        raise HTTPException(status_code=400, detail="操作失败")
    return APIResponse(code=0, data=None, message="举手成功" if hand_data.raised else "已放下手")


@router.post("/{classroom_id}/poll", summary="发起投票")
async def create_poll(
    classroom_id: int,
    poll_data: PollCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """教师发起课堂投票"""
    service = ClassroomService(db)
    result = await service.create_poll(
        classroom_id=classroom_id,
        teacher_id=current_user.id,
        question=poll_data.question,
        options=poll_data.options,
        poll_type=poll_data.poll_type,
        is_anonymous=poll_data.is_anonymous,
        bypass_owner_check=current_user.role == "super_admin",
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/{classroom_id}/poll/{poll_id}/vote", summary="投票")
async def vote_poll(
    classroom_id: int,
    poll_id: int,
    vote_data: PollVote,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """学生对投票进行投票"""
    service = ClassroomService(db)
    success = await service.vote_poll(
        poll_id=poll_id,
        user_id=current_user.id,
        selected_options=vote_data.selected_options,
    )
    if not success:
        raise HTTPException(status_code=400, detail="投票失败")
    return APIResponse(code=0, data=None, message="投票成功")


@router.get("/{classroom_id}/poll/{poll_id}/result", summary="投票结果")
async def poll_result(
    classroom_id: int,
    poll_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取投票结果"""
    service = ClassroomService(db)
    result = await service.get_poll_result(
        poll_id=poll_id,
        tenant_id=current_user.tenant_id or 0,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/{classroom_id}/end", summary="结束课堂")
async def end_classroom(
    classroom_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """结束课堂互动"""
    service = ClassroomService(db)
    success = await service.end_classroom(
        classroom_id=classroom_id,
        teacher_id=current_user.id,
        bypass_owner_check=current_user.role == "super_admin",
    )
    if not success:
        raise HTTPException(status_code=400, detail="结束课堂失败")
    return APIResponse(code=0, data=None, message="课堂已结束")
