"""
智慧学伴 通知 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Notification(Base):
    """通知表"""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="通知ID")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True, comment="租户ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="接收用户ID")
    notification_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True, comment="通知类型: system/course/assignment/social/ai")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="通知标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="通知内容")
    link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="关联链接")
    sender_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, comment="发送者用户ID")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已读")
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="已读时间")
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="元数据(JSON)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")


class NotificationSetting(Base):
    """通知设置表"""

    __tablename__ = "notification_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="设置ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False, comment="用户ID")
    system_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="系统通知")
    course_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="课程通知")
    assignment_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="作业通知")
    social_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="社交通知")
    ai_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="AI通知")
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="邮件推送")
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="推送通知")
    quiet_hours_start: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, comment="免打扰开始时间 HH:MM")
    quiet_hours_end: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, comment="免打扰结束时间 HH:MM")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
