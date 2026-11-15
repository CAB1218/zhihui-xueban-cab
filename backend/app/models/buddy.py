"""
智慧学伴 学伴 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Buddy(Base):
    """学伴表"""

    __tablename__ = "buddies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="学伴ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False, comment="用户ID")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="学伴名称")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="头像URL")
    personality: Mapped[str] = mapped_column(String(30), default="encouraging", nullable=False, comment="人设: encouraging/strict/humorous/gentle")
    tone: Mapped[str] = mapped_column(String(30), default="friendly", nullable=False, comment="语气: friendly/formal/casual")
    interaction_mode: Mapped[str] = mapped_column(String(30), default="proactive", nullable=False, comment="互动模式: proactive/passive/balanced")
    mood: Mapped[str] = mapped_column(String(20), default="happy", nullable=False, comment="心情: happy/excited/thinking/concerned")
    mood_score: Mapped[float] = mapped_column(Float, default=80.0, nullable=False, comment="心情分数(0-100)")
    experience_points: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="经验值")
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="等级")
    custom_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="自定义提示词")
    settings: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="学伴配置(JSON)")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
