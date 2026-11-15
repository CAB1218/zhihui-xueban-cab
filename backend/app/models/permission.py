"""
智慧学伴 RBAC 权限 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Role(Base):
    """角色表"""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="角色ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="角色名称: student/teacher/admin/super_admin")
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="显示名称")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="角色描述")
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否系统内置角色")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class Permission(Base):
    """权限表"""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="权限ID")
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, comment="权限标识: resource:create/note:delete/...")
    display_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="显示名称")
    module: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="所属模块: auth/user/course/resource/...")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="权限描述")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")


class RolePermission(Base):
    """角色-权限关联表"""

    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="关联ID")
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False, index=True, comment="角色ID")
    permission_id: Mapped[int] = mapped_column(Integer, ForeignKey("permissions.id"), nullable=False, index=True, comment="权限ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")


class UserRole(Base):
    """用户-角色关联表"""

    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="关联ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey("roles.id"), nullable=False, index=True, comment="角色ID")
    scope: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="作用域: global/course:{id}/tenant:{id}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
