"""
智慧学伴 笔记 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Note(Base):
    """笔记表"""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="笔记ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="笔记标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="笔记内容(富文本/Markdown)")
    content_plain: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="纯文本内容(用于搜索)")
    note_type: Mapped[str] = mapped_column(String(20), default="personal", nullable=False, comment="笔记类型: personal/course/ai_generated")
    course_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True, index=True, comment="关联课程ID")
    resource_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("resources.id"), nullable=True, comment="关联资源ID")
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所有者用户ID")
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="标签(JSON数组)")
    ai_enhanced: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否经过AI增强")
    share_code: Mapped[Optional[str]] = mapped_column(String(50), unique=True, nullable=True, comment="分享码")
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="字数")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="版本号")
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否已删除")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="删除时间")


class NoteVersion(Base):
    """笔记版本表"""

    __tablename__ = "note_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="版本ID")
    note_id: Mapped[int] = mapped_column(Integer, ForeignKey("notes.id"), nullable=False, index=True, comment="笔记ID")
    version: Mapped[int] = mapped_column(Integer, nullable=False, comment="版本号")
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="版本标题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="版本内容")
    change_summary: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="变更摘要")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
