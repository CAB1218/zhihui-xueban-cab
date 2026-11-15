"""
智慧学伴 帮助文章 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HelpArticle(Base):
    """帮助文章表"""

    __tablename__ = "help_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="文章ID")
    category: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="分类: getting_started/features/faq/troubleshooting")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="内容(Markdown)")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="排序")
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览次数")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否发布")
    is_faq: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否为FAQ")
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="标签(JSON)")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
