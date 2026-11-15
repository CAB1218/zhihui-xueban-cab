"""
智慧学伴 资源 ORM 模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Resource(Base):
    """资源表 - 课程资料/文档/视频等"""

    __tablename__ = "resources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="资源ID")
    tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID")
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="资源标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="资源描述")
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True, comment="资源类型: pdf/docx/pptx/video/audio/image/other")
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="MIME类型")
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="文件大小(字节)")
    file_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="对象存储Key")
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True, comment="访问URL")
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="缩略图URL")
    course_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True, index=True, comment="关联课程ID")
    uploader_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, comment="上传者用户ID")
    download_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="下载次数")
    view_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览次数")
    tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="标签(JSON数组)")
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="元数据(JSON)")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否公开")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="软删除时间")


class ResourceFavorite(Base):
    """资源收藏表"""

    __tablename__ = "resource_favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey("resources.id"), nullable=False, index=True, comment="资源ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, comment="收藏时间")
