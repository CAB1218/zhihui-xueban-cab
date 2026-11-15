"""
智慧学伴 课堂互动 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Classroom(Base):
    """课堂互动表"""

    __tablename__ = "classrooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="课堂ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False, index=True, comment="课程ID")
    teacher_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="教师ID")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="课堂主题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="课堂描述")
    status: Mapped[str] = mapped_column(String(20), default="scheduled", nullable=False, index=True, comment="状态: scheduled/active/ended")
    access_code: Mapped[Optional[str]] = mapped_column(String(10), unique=True, nullable=True, comment="加入码")
    max_participants: Mapped[int] = mapped_column(Integer, default=100, nullable=False, comment="最大参与人数")
    participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="当前参与人数")
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="课堂配置(JSON)")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="开始时间")
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="结束时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class ClassroomParticipant(Base):
    """课堂参与者表"""

    __tablename__ = "classroom_participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="参与者ID")
    classroom_id: Mapped[int] = mapped_column(Integer, ForeignKey("classrooms.id"), nullable=False, index=True, comment="课堂ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    role: Mapped[str] = mapped_column(String(20), default="student", nullable=False, comment="角色: teacher/assistant/student")
    hand_raised: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否举手")
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="加入时间")
    left_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="离开时间")


class ClassroomPoll(Base):
    """课堂投票表"""

    __tablename__ = "classroom_polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="投票ID")
    classroom_id: Mapped[int] = mapped_column(Integer, ForeignKey("classrooms.id"), nullable=False, index=True, comment="课堂ID")
    question: Mapped[str] = mapped_column(String(500), nullable=False, comment="投票问题")
    options: Mapped[str] = mapped_column(Text, nullable=False, comment="选项(JSON数组)")
    poll_type: Mapped[str] = mapped_column(String(20), default="single", nullable=False, comment="类型: single/multiple")
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否匿名")
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, comment="状态: active/closed")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="创建者")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="关闭时间")


class ClassroomPollVote(Base):
    """课堂投票记录表"""

    __tablename__ = "classroom_poll_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="投票记录ID")
    poll_id: Mapped[int] = mapped_column(Integer, ForeignKey("classroom_polls.id"), nullable=False, index=True, comment="投票ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    selected_options: Mapped[str] = mapped_column(Text, nullable=False, comment="选中的选项(JSON数组)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="投票时间")
