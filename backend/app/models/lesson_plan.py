"""
智慧学伴 教案 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LessonPlan(Base):
    """教案表"""

    __tablename__ = "lesson_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="教案ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False, index=True, comment="课程ID")
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="教师ID")
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="教案标题")
    objectives: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="教学目标(JSON)")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="教案内容(富文本)")
    materials: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="教学材料(JSON)")
    duration_minutes: Mapped[int] = mapped_column(Integer, default=45, nullable=False, comment="时长(分钟)")
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否AI生成")
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, comment="状态: draft/published/archived")
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="版本号")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
