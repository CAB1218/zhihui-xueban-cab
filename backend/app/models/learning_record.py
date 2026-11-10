"""
AI4EDU 学情记录 ORM 模型
任务2（理解学生-学生学习情况分析）：存储原始学情记录，供数据质量检查与个体/群体分析使用

记录刻意保留为「原始态」：字段允许为空、允许存在异常值与重复条目，
质量检查与清洗在服务层完成，避免在入库阶段就把问题掩盖掉。
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LearningRecord(Base):
    """学情记录表 — 每次作答/测验/课堂互动产生一条原始记录"""

    __tablename__ = "learning_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="学生ID"
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("courses.id"), nullable=True, index=True, comment="课程ID（可能缺失）"
    )

    # 学习内容维度
    knowledge_point: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, index=True, comment="知识点名称（可能缺失）"
    )
    record_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="quiz", comment="quiz/homework/exam/classroom/self_test"
    )
    source_ref: Mapped[Optional[str]] = mapped_column(
        String(120), nullable=True, comment="来源标识（试卷/题目集编号），用于溯源"
    )

    # 作答结果
    question_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="该次作答题目数")
    is_correct: Mapped[Optional[bool]] = mapped_column(
        Boolean, nullable=True, comment="单题对错（整体性记录可能为空）"
    )
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="得分（可能缺失）")
    max_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="满分，用于识别超范围分数")
    duration_seconds: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="作答耗时（秒），用于识别异常值"
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True, comment="记录发生时间"
    )

    # 数据属性
    is_simulated: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否为模拟数据（演示用，便于如实标注来源）"
    )
    raw_payload: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="原始记录 JSON，保留采集时的完整信息"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="入库时间"
    )

    __table_args__ = (
        Index("ix_learning_records_student_course", "student_id", "course_id"),
        Index("ix_learning_records_course_kp", "course_id", "knowledge_point"),
    )
