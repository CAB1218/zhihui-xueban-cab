"""
智慧学伴 学生评价 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudentEvaluation(Base):
    """学生评价表 — 教师对学生的成长评价"""

    __tablename__ = "student_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="评价ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="学生用户ID")
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="教师用户ID")
    course_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True, index=True, comment="关联课程ID(可选)")
    evaluation_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="评价类型: overall/academic/attitude/improvement")
    rating: Mapped[int] = mapped_column(Integer, nullable=False, comment="评分1-5星")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="评价内容")
    suggestion: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="学习建议")
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否对学生可见")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
