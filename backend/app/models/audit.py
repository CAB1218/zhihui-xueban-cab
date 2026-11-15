"""
智慧学伴 审计日志 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    """审计日志表"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="日志ID")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True, comment="操作用户ID")
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="操作类型: create/read/update/delete/login/export")
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="资源类型: user/course/note/resource/...")
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="资源ID")
    detail: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="操作详情(JSON)")
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, comment="IP地址")
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="User-Agent")
    request_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="请求ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True, comment="创建时间")
