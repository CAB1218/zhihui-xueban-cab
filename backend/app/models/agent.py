"""
智慧学伴 AI会话 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentSession(Base):
    """AI会话表"""

    __tablename__ = "agent_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="会话ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    agent_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True, comment="智能体类型: tutor/study_buddy/examiner/assistant")
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="会话标题")
    scene_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="场景类型")
    course_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True, comment="关联课程ID")
    model_name: Mapped[str] = mapped_column(String(50), default="gpt-4o", nullable=False, comment="模型名称")
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="系统提示词")
    context: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="会话上下文(JSON)")
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="消息数量")
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="总Token消耗")
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否归档")
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="最后消息时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class AgentMessage(Base):
    """AI消息表"""

    __tablename__ = "agent_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="消息ID")
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("agent_sessions.id"), nullable=False, index=True, comment="会话ID")
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="角色: user/assistant/system")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    content_type: Mapped[str] = mapped_column(String(20), default="text", nullable=False, comment="内容类型: text/markdown/code/image")
    tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Token数量")
    model_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="使用的模型")
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="元数据(JSON)")
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("agent_messages.id"), nullable=True, comment="父消息ID(分支对话)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
