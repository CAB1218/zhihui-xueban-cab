"""
AI4EDU 课程梳理 ORM 模型
任务1（理解学科-学习内容与要求梳理）：存储用户输入的课程与 AI 梳理产出的大纲
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CurriculumOutline(Base):
    """课程梳理大纲表 — 用户指定课程后由系统检索+LLM 梳理生成"""

    __tablename__ = "curriculum_outlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="大纲ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="发起梳理的用户ID")

    # 用户输入
    course_query: Mapped[str] = mapped_column(String(200), nullable=False, comment="用户输入的课程（如：初中数学七年级上册）")
    subject: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="识别出的学科ID（math/physics/...）")
    grade_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="学段/年级（如：七年级）")
    scope_hint: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="用户补充的范围说明（教材版本/章节限定等）")

    # 产出
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="大纲标题")
    outline: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="完整大纲 JSON（units/connections/sources）")
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="联网检索到的原始材料出处 JSON")
    model_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="生成时使用的 LLM")
    used_web_search: Mapped[Optional[bool]] = mapped_column(nullable=True, comment="是否成功使用了联网检索结果")

    # 状态
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True, comment="pending/completed/failed")
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="失败原因")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
