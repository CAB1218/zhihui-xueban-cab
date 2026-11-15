"""
智慧学伴 用户 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=True, comment="租户ID")
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True, comment="邮箱")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True, comment="手机号")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment="昵称")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="头像URL")
    role: Mapped[str] = mapped_column(String(20), default="student", nullable=False, index=True, comment="角色: student/teacher/admin/super_admin")
    grade: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="年级")
    school: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="学校")
    major: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="专业")
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="个人简介")
    preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="用户偏好(JSON)")
    default_scene: Mapped[str] = mapped_column(String(20), default="classroom", nullable=False, comment="默认场景")
    locale: Mapped[str] = mapped_column(String(10), default="zh-CN", nullable=False, comment="语言偏好")
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Shanghai", nullable=False, comment="时区")
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否完成引导")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="最后登录时间")
    last_login_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True, comment="最后登录IP")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="软删除时间")
