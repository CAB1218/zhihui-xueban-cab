"""
智慧学伴 租户 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Tenant(Base):
    """租户表 - 支持多租户隔离"""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="租户ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="租户名称")
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="租户标识（URL友好）")
    schema_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="数据库Schema名称")
    domain: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, comment="绑定域名")
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="Logo URL")
    plan: Mapped[str] = mapped_column(String(20), default="free", nullable=False, comment="套餐: free/basic/premium/enterprise")
    max_users: Mapped[int] = mapped_column(Integer, default=50, nullable=False, comment="最大用户数")
    max_storage_mb: Mapped[int] = mapped_column(Integer, default=1024, nullable=False, comment="最大存储空间(MB)")
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="租户配置(JSON)")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
