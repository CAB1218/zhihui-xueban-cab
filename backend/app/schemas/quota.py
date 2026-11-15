"""
智慧学伴 配额管理相关 Pydantic Schema
v2 新增：多租户模型配额计量
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TenantQuotaResponse(BaseModel):
    """租户配额响应"""

    tenant_id: int = Field(..., description="租户ID")
    daily_token_limit: int = Field(..., description="每日token上限")
    monthly_token_limit: int = Field(..., description="每月token上限")
    daily_used: int = Field(0, description="今日已用token")
    monthly_used: int = Field(0, description="本月已用token")
    strategy: str = Field("latency", description="负载均衡策略")
    sticky_model: Optional[str] = Field(None, description="sticky 模型")
    is_active: bool = Field(True, description="是否启用")
    usage_percentage: float = Field(0.0, description="日使用率百分比")


class TenantQuotaUpdate(BaseModel):
    """更新租户配额请求"""

    daily_token_limit: Optional[int] = Field(None, description="每日token上限")
    monthly_token_limit: Optional[int] = Field(None, description="每月token上限")
    strategy: Optional[str] = Field(None, description="策略: latency/weighted/sticky")
    sticky_model: Optional[str] = Field(None, description="sticky 模型")
    is_active: Optional[bool] = Field(None, description="是否启用")


class QuotaDashboardData(BaseModel):
    """配额看板汇总数据"""

    tenants: List[TenantQuotaResponse] = Field(default_factory=list, description="租户配额列表")
    total_daily_used: int = Field(0, description="全部租户今日总用量")
    total_daily_limit: int = Field(0, description="全部租户今日总限额")
    top_consumers: List[Dict[str, Any]] = Field(
        default_factory=list, description="Top 5 消费租户"
    )


class UsageTrendItem(BaseModel):
    """用量趋势项"""

    date: str = Field(..., description="日期 YYYY-MM-DD")
    total_tokens: int = Field(0, description="当日总token")
    request_count: int = Field(0, description="当日请求数")


class ModelUsageDetail(BaseModel):
    """各模型用量明细"""

    provider: str = Field(..., description="提供商")
    model_name: str = Field(..., description="模型名称")
    request_count: int = Field(0, description="调用次数")
    total_tokens: int = Field(0, description="总token用量")
    avg_latency_ms: float = Field(0.0, description="平均延迟(毫秒)")
