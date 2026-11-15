"""
智慧学伴 对话导出记录 ORM 模型
v2 新增：支持对话导出 PDF/Markdown
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AgentExport(Base):
    """对话导出记录"""

    __tablename__ = "agent_exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="导出ID")
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("agent_sessions.id"), nullable=False, index=True, comment="会话ID"
    )
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID"
    )
    export_format: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="导出格式: pdf/markdown"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, comment="状态: pending/processing/completed/failed"
    )
    file_key: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="MinIO 存储 Key"
    )
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="文件大小(字节)")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True, comment="创建时间"
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="完成时间"
    )
    expired_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, comment="预签名 URL 过期时间"
    )

    def to_dict(self) -> dict:
        """转为字典"""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "export_format": self.export_format,
            "status": self.status,
            "file_size": self.file_size,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "expired_at": self.expired_at.isoformat() if self.expired_at else None,
        }
