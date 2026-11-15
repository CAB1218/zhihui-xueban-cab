"""
智慧学伴 场景 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Scene(Base):
    """场景配置表 - 定义各场景的主题和功能"""

    __tablename__ = "scenes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="场景ID")
    scene_type: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, comment="场景类型: classroom/self_study/exam/discussion")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="场景名称")
    name_en: Mapped[str] = mapped_column(String(50), nullable=False, comment="场景英文名")
    icon: Mapped[str] = mapped_column(String(50), nullable=False, comment="图标标识")
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, comment="主题色(Hex)")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="场景描述")
    layout_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="布局配置(JSON)")
    feature_flags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="功能开关(JSON)")
    default_widgets: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="默认组件列表(JSON)")
    ai_prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="AI提示词模板")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")


class UserScenePreference(Base):
    """用户场景偏好表"""

    __tablename__ = "user_scene_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="偏好ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    scene_type: Mapped[str] = mapped_column(String(30), nullable=False, comment="场景类型")
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否为当前场景")
    custom_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="自定义配置(JSON)")
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="最后访问时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
