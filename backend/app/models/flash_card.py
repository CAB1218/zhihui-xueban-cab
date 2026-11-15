"""
智慧学伴 复习卡片 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FlashCard(Base):
    """复习卡片表 - 间隔重复学习"""

    __tablename__ = "flash_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="卡片ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    course_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True, comment="课程ID")
    diagnosis_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("diagnoses.id"), nullable=True, comment="关联诊断ID")
    front: Mapped[str] = mapped_column(Text, nullable=False, comment="正面内容(问题)")
    back: Mapped[str] = mapped_column(Text, nullable=False, comment="背面内容(答案)")
    card_type: Mapped[str] = mapped_column(String(20), default="basic", nullable=False, comment="卡片类型: basic/cloze/reverse")
    knowledge_point: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="知识点")
    difficulty: Mapped[str] = mapped_column(String(10), default="medium", nullable=False, comment="难度: easy/medium/hard")
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否AI生成")
    # 间隔重复字段
    repetition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="复习次数")
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False, comment="易度因子(SM-2算法)")
    interval_days: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="间隔天数")
    next_review_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="下次复习时间")
    last_reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="上次复习时间")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
