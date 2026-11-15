"""
智慧学伴 学习诊断 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Diagnosis(Base):
    """诊断表"""

    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="诊断ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    course_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True, comment="课程ID")
    diagnosis_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="诊断类型: knowledge/comprehensive/unit")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="诊断标题")
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, comment="状态: pending/in_progress/completed")
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="总题数")
    correct_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="正确题数")
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True, comment="得分")
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="用时(秒)")
    weaknesses: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="知识弱点(JSON)")
    strengths: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="知识强项(JSON)")
    recommendations: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="学习建议(JSON)")
    report_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="报告文件URL")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="开始时间")
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="完成时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class DiagnosisQuestion(Base):
    """诊断题目表"""

    __tablename__ = "diagnosis_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="题目ID")
    diagnosis_id: Mapped[int] = mapped_column(Integer, ForeignKey("diagnoses.id"), nullable=False, index=True, comment="诊断ID")
    question_text: Mapped[str] = mapped_column(Text, nullable=False, comment="题目内容")
    question_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="题型: choice/blank/essay")
    options: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="选项(JSON)")
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False, comment="正确答案")
    user_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="用户答案")
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, comment="是否正确")
    knowledge_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="关联知识点(JSON)")
    difficulty: Mapped[str] = mapped_column(String(10), default="medium", nullable=False, comment="难度: easy/medium/hard")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
