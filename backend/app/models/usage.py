"""
智慧学伴 LLM 用量日志 + 租户配额 ORM 模型
v2 新增：支持多租户模型配额计量
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LLMUsageLog(Base):
    """LLM 调用用量日志，每次 call_llm 记录一条"""

    __tablename__ = "llm_usage_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="日志ID")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, index=True, comment="用户ID"
    )
    session_id: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True, comment="会话ID"
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False, comment="模型提供商")
    model_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="模型名称")
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="输入token数")
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="输出token数")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="总token数")
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="响应耗时(毫秒)")
    status: Mapped[str] = mapped_column(
        String(20), default="success", nullable=False, comment="状态: success/failed/quota_exceeded"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True, comment="创建时间"
    )

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "provider": self.provider,
            "model_name": self.model_name,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class TenantQuota(Base):
    """租户配额配置"""

    __tablename__ = "tenant_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="配额ID")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, unique=True, index=True, comment="租户ID"
    )
    daily_token_limit: Mapped[int] = mapped_column(
        Integer, default=500000, nullable=False, comment="每日token上限"
    )
    monthly_token_limit: Mapped[int] = mapped_column(
        Integer, default=10000000, nullable=False, comment="每月token上限"
    )
    strategy: Mapped[str] = mapped_column(
        String(20), default="latency", nullable=False, comment="负载均衡策略: latency/weighted/sticky"
    )
    sticky_model: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="sticky 策略下锁定的模型"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间"
    )
