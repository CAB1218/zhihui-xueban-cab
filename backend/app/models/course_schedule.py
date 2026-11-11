"""
AI4EDU 个人课表 ORM 模型

用途：让用户（学生 / 教师）把自己手上的课程表导入系统，
场景仪表盘的「今日课表」「今日课程」统计据此展示真实数据，
而不是一直用内置示例课表。

设计要点：
- 以「星期 + 起始/结束时间」存储，天然支持整学期循环课表（不绑定具体日期）
- weekday 采用 ISO 约定：1=周一 … 7=周日
- start_time / end_time 用 'HH:mm' 字符串存储，便于直接比对与排序
- source_file 记录来源文件名，便于用户回溯「这份课表是从哪个文件导入的」
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CourseSchedule(Base):
    """用户个人课表条目 — 一条记录 = 每周某天的一节课"""

    __tablename__ = "course_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="课表条目ID")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="课表所属用户ID"
    )

    # 课程信息
    course_name: Mapped[str] = mapped_column(String(120), nullable=False, comment="课程名称")
    teacher: Mapped[Optional[str]] = mapped_column(String(60), nullable=True, comment="任课教师")
    location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, comment="上课地点")

    # 时间信息
    weekday: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="星期（1=周一 … 7=周日）"
    )
    start_time: Mapped[str] = mapped_column(String(5), nullable=False, comment="开始时间 HH:mm")
    end_time: Mapped[str] = mapped_column(String(5), nullable=False, comment="结束时间 HH:mm")
    weeks: Mapped[Optional[str]] = mapped_column(
        String(60), nullable=True, comment="上课周次，如 1-16 / 1,3,5，可为空表示全学期"
    )

    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
    source_file: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="导入来源文件名，用于回溯"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间"
    )

    __table_args__ = (
        Index("ix_course_schedules_user_weekday", "user_id", "weekday"),
    )
