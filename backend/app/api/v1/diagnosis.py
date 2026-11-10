"""
AI4Edu 学习诊断 API
提供知识诊断、学习报告、弱点分析等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.diagnosis import AnswerSubmit, DiagnosisCreate, DiagnosisResponse
from app.services.diagnosis_service import DiagnosisService

router = APIRouter()


@router.post("/start", summary="启动诊断")
async def start_diagnosis(
    diagnosis_data: DiagnosisCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """启动知识诊断评估"""
    service = DiagnosisService(db)
    result = await service.start_diagnosis(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        diagnosis_type=diagnosis_data.diagnosis_type,
        title=diagnosis_data.title,
        course_id=diagnosis_data.course_id,
        subject=diagnosis_data.subject,
        knowledge_points=diagnosis_data.knowledge_points,
        question_count=diagnosis_data.question_count,
    )
    return APIResponse(code=0, data=result, message="success")


# 注意：静态路径必须定义在 /{diagnosis_id} 之前，否则 "history" 会被当作路径参数解析
@router.get("/history", summary="诊断历史")
async def diagnosis_history(
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取历史诊断记录"""
    service = DiagnosisService(db)
    result = await service.get_history(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        limit=limit,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/{diagnosis_id}/submit", summary="提交答案")
async def submit_answers(
    diagnosis_id: int,
    answer_data: AnswerSubmit,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """提交诊断答案"""
    service = DiagnosisService(db)
    result = await service.submit_answers(
        diagnosis_id=diagnosis_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        answers=answer_data.answers,
        duration_seconds=answer_data.duration_seconds,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/{diagnosis_id}", summary="获取诊断结果")
async def get_diagnosis(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取诊断结果详情"""
    service = DiagnosisService(db)
    result = await service.get_diagnosis(
        diagnosis_id=diagnosis_id,
        tenant_id=current_user.tenant_id or 0,
    )
    if not result:
        raise HTTPException(status_code=404, detail="诊断不存在")
    return APIResponse(code=0, data=result, message="success")


@router.get("/{diagnosis_id}/report", summary="获取诊断报告")
async def get_diagnosis_report(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取详细诊断报告（含知识弱点分析）"""
    service = DiagnosisService(db)
    result = await service.get_report(
        diagnosis_id=diagnosis_id,
        tenant_id=current_user.tenant_id or 0,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/{diagnosis_id}/weaknesses", summary="获取知识弱点")
async def get_weaknesses(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取诊断发现的知识弱点列表"""
    service = DiagnosisService(db)
    result = await service.get_weaknesses(
        diagnosis_id=diagnosis_id,
        tenant_id=current_user.tenant_id or 0,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/{diagnosis_id}/review-cards", summary="生成复习卡片")
async def generate_review_cards(
    diagnosis_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """基于诊断结果生成个性化复习卡片"""
    service = DiagnosisService(db)
    result = await service.generate_review_cards(
        diagnosis_id=diagnosis_id,
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")
