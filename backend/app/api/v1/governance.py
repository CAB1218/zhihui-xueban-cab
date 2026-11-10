"""
AI4Edu 数据治理 API
提供数据导出、审计日志、隐私设置等端点
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse, PaginationParams
from app.services.governance_service import GovernanceService

router = APIRouter()


class PrivacySettingsUpdate(BaseModel):
    """隐私设置更新"""

    data_classification_enabled: Optional[bool] = None
    audit_logging_enabled: Optional[bool] = None
    auto_delete_enabled: Optional[bool] = None
    sensitive_data_masking: Optional[bool] = None


@router.get("/audit-logs", summary="获取审计日志")
async def list_audit_logs(
    pagination: PaginationParams = Depends(),
    action_type: Optional[str] = Query(None, description="操作类型筛选"),
    user_id: Optional[int] = Query(None, description="用户ID筛选"),
    start_date: Optional[str] = Query(None, description="开始日期"),
    end_date: Optional[str] = Query(None, description="结束日期"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取审计日志列表"""
    service = GovernanceService(db)
    result = await service.list_audit_logs(
        tenant_id=current_user.tenant_id or 0,
        pagination=pagination,
        action_type=action_type,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )
    return APIResponse(code=0, data=result.model_dump(), message="success")


@router.post("/export", summary="导出用户数据")
async def export_user_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """导出当前用户的所有数据（GDPR合规）"""
    service = GovernanceService(db)
    result = await service.export_user_data(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.delete("/delete-account", summary="删除账户")
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """删除用户账户及所有关联数据"""
    service = GovernanceService(db)
    success = await service.delete_account(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    if not success:
        raise HTTPException(status_code=404, detail="用户不存在")
    return APIResponse(code=0, data=None, message="账户删除请求已处理")


@router.get("/privacy-settings", summary="获取隐私设置")
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取当前用户的隐私设置"""
    service = GovernanceService(db)
    result = await service.get_privacy_settings(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=result, message="success")


@router.put("/privacy-settings", summary="更新隐私设置")
async def update_privacy_settings(
    settings_data: PrivacySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """更新隐私设置"""
    service = GovernanceService(db)
    update_kwargs = {
        k: v for k, v in settings_data.model_dump().items() if v is not None
    }
    result = await service.update_privacy_settings(
        tenant_id=current_user.tenant_id or 0,
        user_id=current_user.id,
        **update_kwargs,
    )
    return APIResponse(code=0, data=result, message="success")


@router.get("/data-retention", summary="数据保留策略")
async def get_data_retention_policy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """获取数据保留策略信息"""
    service = GovernanceService(db)
    result = await service.get_data_retention_policy(
        tenant_id=current_user.tenant_id or 0,
    )
    return APIResponse(code=0, data=result, message="success")


@router.post("/scan", summary="敏感数据扫描")
async def scan_sensitive_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    """扫描库表结构，输出敏感字段暴露面（只读，不采样真实数据行）"""
    service = GovernanceService(db)
    result = await service.scan_sensitive_fields(tenant_id=current_user.tenant_id or 0)
    return APIResponse(code=0, data=result, message="success")
