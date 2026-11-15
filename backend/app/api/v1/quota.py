"""
智慧学伴 配额管理 API 端点
管理员可查看/配置各租户的配额和使用情况

端点:
- GET  /admin/quotas               获取所有租户配额列表
- GET  /admin/quotas/{tenant_id}   获取指定租户配额详情
- PUT  /admin/quotas/{tenant_id}   更新租户配额配置
- GET  /admin/quotas/{tenant_id}/usage  获取租户用量明细（含趋势）
- GET  /admin/quotas/dashboard     配额看板汇总数据
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.dependencies import get_current_user, require_role
from app.models.usage import LLMUsageLog, TenantQuota
from app.models.user import User
from app.schemas.common import APIResponse
from app.schemas.quota import TenantQuotaUpdate
from app.services.quota_manager import quota_manager

logger = logging.getLogger(__name__)

router = APIRouter()


async def _get_db():
    """获取异步数据库会话"""
    from app.database import get_db
    async for session in get_db():
        yield session


@router.get("", summary="获取所有租户配额列表")
async def list_quotas(
    current_user: User = Depends(require_role(["super_admin", "admin"])),
    db: AsyncSession = Depends(_get_db),
) -> APIResponse:
    """获取所有租户的配额配置和使用情况"""
    stmt = select(TenantQuota).order_by(TenantQuota.tenant_id)
    result = await db.execute(stmt)
    quotas = result.scalars().all()

    items = []
    for q in quotas:
        usage = await quota_manager.get_usage(q.tenant_id, db)
        usage_pct = round(q.daily_token_limit and usage["daily_used"] / q.daily_token_limit * 100 or 0, 2)
        items.append({
            "tenant_id": q.tenant_id,
            "daily_token_limit": q.daily_token_limit,
            "monthly_token_limit": q.monthly_token_limit,
            "daily_used": usage["daily_used"],
            "monthly_used": usage["monthly_used"],
            "strategy": q.strategy,
            "sticky_model": q.sticky_model,
            "is_active": q.is_active,
            "usage_percentage": usage_pct,
        })

    return APIResponse(code=0, data=items, message="success")


@router.get("/dashboard", summary="配额看板汇总数据")
async def get_dashboard(
    current_user: User = Depends(require_role(["super_admin", "admin"])),
    db: AsyncSession = Depends(_get_db),
) -> APIResponse:
    """配额看板汇总：总用量、总限额、Top 5 消费租户"""
    stmt = select(TenantQuota).order_by(TenantQuota.tenant_id)
    result = await db.execute(stmt)
    quotas = result.scalars().all()

    tenants_data = []
    total_daily_used = 0
    total_daily_limit = 0

    for q in quotas:
        usage = await quota_manager.get_usage(q.tenant_id, db)
        usage_pct = round(q.daily_token_limit and usage["daily_used"] / q.daily_token_limit * 100 or 0, 2)
        total_daily_used += usage["daily_used"]
        total_daily_limit += q.daily_token_limit

        tenants_data.append({
            "tenant_id": q.tenant_id,
            "daily_token_limit": q.daily_token_limit,
            "monthly_token_limit": q.monthly_token_limit,
            "daily_used": usage["daily_used"],
            "monthly_used": usage["monthly_used"],
            "strategy": q.strategy,
            "sticky_model": q.sticky_model,
            "is_active": q.is_active,
            "usage_percentage": usage_pct,
        })

    # Top 5 消费租户（按 daily_used 排序）
    top_consumers = sorted(tenants_data, key=lambda x: x["daily_used"], reverse=True)[:5]

    return APIResponse(
        code=0,
        data={
            "tenants": tenants_data,
            "total_daily_used": total_daily_used,
            "total_daily_limit": total_daily_limit,
            "top_consumers": top_consumers,
        },
        message="success",
    )


@router.get("/{tenant_id}", summary="获取指定租户配额详情")
async def get_quota(
    tenant_id: int,
    current_user: User = Depends(require_role(["super_admin", "admin"])),
    db: AsyncSession = Depends(_get_db),
) -> APIResponse:
    """获取指定租户的配额配置和当前用量"""
    stmt = select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
    result = await db.execute(stmt)
    quota = result.scalars().first()

    if not quota:
        raise HTTPException(status_code=404, detail="租户配额配置不存在")

    usage = await quota_manager.get_usage(tenant_id, db)
    usage_pct = round(quota.daily_token_limit and usage["daily_used"] / quota.daily_token_limit * 100 or 0, 2)

    return APIResponse(
        code=0,
        data={
            "tenant_id": quota.tenant_id,
            "daily_token_limit": quota.daily_token_limit,
            "monthly_token_limit": quota.monthly_token_limit,
            "daily_used": usage["daily_used"],
            "monthly_used": usage["monthly_used"],
            "daily_req_count": usage["daily_req_count"],
            "strategy": quota.strategy,
            "sticky_model": quota.sticky_model,
            "is_active": quota.is_active,
            "usage_percentage": usage_pct,
        },
        message="success",
    )


@router.put("/{tenant_id}", summary="更新租户配额配置")
async def update_quota(
    tenant_id: int,
    update_data: TenantQuotaUpdate,
    current_user: User = Depends(require_role(["super_admin"])),
    db: AsyncSession = Depends(_get_db),
) -> APIResponse:
    """更新租户的配额上限和策略配置"""
    stmt = select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
    result = await db.execute(stmt)
    quota = result.scalars().first()

    if not quota:
        # 创建新配置
        quota = TenantQuota(
            tenant_id=tenant_id,
            daily_token_limit=settings.QUOTA_DEFAULT_DAILY_TOKENS,
            monthly_token_limit=settings.QUOTA_DEFAULT_MONTHLY_TOKENS,
            strategy=settings.LLM_BALANCER_STRATEGY,
            is_active=True,
        )
        db.add(quota)

    # 更新字段
    if update_data.daily_token_limit is not None:
        quota.daily_token_limit = update_data.daily_token_limit
    if update_data.monthly_token_limit is not None:
        quota.monthly_token_limit = update_data.monthly_token_limit
    if update_data.strategy is not None:
        quota.strategy = update_data.strategy
    if update_data.sticky_model is not None:
        quota.sticky_model = update_data.sticky_model
    if update_data.is_active is not None:
        quota.is_active = update_data.is_active

    await db.flush()

    return APIResponse(
        code=0,
        data={
            "tenant_id": quota.tenant_id,
            "daily_token_limit": quota.daily_token_limit,
            "monthly_token_limit": quota.monthly_token_limit,
            "strategy": quota.strategy,
            "sticky_model": quota.sticky_model,
            "is_active": quota.is_active,
        },
        message="配额配置已更新",
    )


@router.get("/{tenant_id}/usage", summary="获取租户用量明细（含趋势）")
async def get_usage_detail(
    tenant_id: int,
    days: int = Query(7, description="趋势天数", ge=1, le=30),
    current_user: User = Depends(require_role(["super_admin", "admin"])),
    db: AsyncSession = Depends(_get_db),
) -> APIResponse:
    """获取租户用量明细，包含最近 N 天的趋势数据"""
    # 当前用量
    usage = await quota_manager.get_usage(tenant_id, db)

    # 最近 N 天的趋势（从 llm_usage_logs 聚合）
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    stmt = (
        select(
            func.date_trunc("day", LLMUsageLog.created_at).label("day"),
            func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
            func.count(LLMUsageLog.id).label("request_count"),
        )
        .where(
            and_(
                LLMUsageLog.tenant_id == tenant_id,
                LLMUsageLog.created_at >= start_date,
            )
        )
        .group_by("day")
        .order_by("day")
    )
    result = await db.execute(stmt)
    trend_rows = result.all()

    trend = [
        {
            "date": row.day.strftime("%Y-%m-%d") if row.day else "",
            "total_tokens": row.total_tokens or 0,
            "request_count": row.request_count or 0,
        }
        for row in trend_rows
    ]

    # 各模型用量明细
    model_stmt = (
        select(
            LLMUsageLog.provider,
            LLMUsageLog.model_name,
            func.count(LLMUsageLog.id).label("request_count"),
            func.sum(LLMUsageLog.total_tokens).label("total_tokens"),
            func.avg(LLMUsageLog.latency_ms).label("avg_latency_ms"),
        )
        .where(
            and_(
                LLMUsageLog.tenant_id == tenant_id,
                LLMUsageLog.created_at >= start_date,
                LLMUsageLog.status == "success",
            )
        )
        .group_by(LLMUsageLog.provider, LLMUsageLog.model_name)
        .order_by(desc("total_tokens"))
    )
    model_result = await db.execute(model_stmt)
    model_rows = model_result.all()

    model_details = [
        {
            "provider": row.provider,
            "model_name": row.model_name,
            "request_count": row.request_count or 0,
            "total_tokens": row.total_tokens or 0,
            "avg_latency_ms": round(float(row.avg_latency_ms or 0), 1),
        }
        for row in model_rows
    ]

    return APIResponse(
        code=0,
        data={
            "current_usage": usage,
            "trend": trend,
            "model_details": model_details,
        },
        message="success",
    )
