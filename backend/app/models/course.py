"""
智慧学伴 课程 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Course(Base):
    """课程表"""

    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="课程ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="课程名称")
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="课程编码")
    subject: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="学科: math/physics/chemistry/...") 
    grade: Mapped[str] = mapped_column(String(20), nullable=False, comment="年级")
    semester: Mapped[str] = mapped_column(String(20), nullable=False, comment="学期: 2024-spring")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="课程描述")
    cover_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="封面URL")
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="教师用户ID")
    graph_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="关联知识图谱ID")
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="课程配置(JSON)")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class CourseEnrollment(Base):
    """课程选课表 - 学生与课程的关联"""

    __tablename__ = "course_enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="选课ID")
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False, index=True, comment="课程ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="学生用户ID")
    role: Mapped[str] = mapped_column(String(20), default="student", nullable=False, comment="角色: student/assistant")
    progress: Mapped[float] = mapped_column(default=0.0, nullable=False, comment="学习进度(0-100)")
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="选课时间")
    dropped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="退课时间")
