"""
AI4EDU 个性化学习建议 ORM 模型
任务3（理解教学-个性化学习建议）：把「学习要求 + 学情结论 + 可用材料」落成一份可执行、可调整的方案

设计要点：
- 方案整体以 JSON 存在 plan_json 里：建议条目、材料清单、先后安排、教师调整建议都是同一份快照
- 冗余存 student_name / course_name，方便列表页直接展示（学生改名也不影响历史方案的可读性）
- source_json 记录生成时用了哪份大纲、多少条记录，便于「结论可追」
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LearningPlan(Base):
    """个性化学习建议方案"""

    __tablename__ = "learning_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="方案ID")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="发起生成的用户ID"
    )

    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="方案面向的学生ID"
    )
    student_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="学生姓名快照"
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("courses.id"), nullable=True, index=True, comment="课程ID"
    )
    course_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="课程名称快照"
    )

    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="方案标题")
    duration_days: Mapped[int] = mapped_column(
        Integer, nullable=False, default=7, comment="建议周期（天）"
    )
    focus: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="教师指定优先补强的知识点"
    )

    plan_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="完整方案 JSON（建议条目/材料/顺序/教师调整）"
    )
    source_json: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="生成依据快照：大纲ID、有效记录数、数据说明"
    )
    model_name: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="生成引擎，如 rule+outline"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed", index=True, comment="completed/failed"
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="失败原因")

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间"
    )
