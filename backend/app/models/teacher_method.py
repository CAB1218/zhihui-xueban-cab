"""
智慧学伴 老师方法 & 课堂记录 ORM 模型
存储老师讲授的解题方法、课堂录播/板书结构化记录
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TeacherMethod(Base):
    """老师方法表 - 存储老师讲授的解题方法/知识点讲解"""

    __tablename__ = "teacher_methods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="方法ID")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="教师用户ID"
    )
    course_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("courses.id"), nullable=True, index=True, comment="关联课程ID"
    )
    classroom_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("classrooms.id"), nullable=True, comment="关联课堂ID"
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False, comment="方法标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="方法内容(结构化文本)")
    method_type: Mapped[str] = mapped_column(
        String(30), nullable=False, comment="类型: board_note/video_transcript/textbook_solution/manual"
    )
    knowledge_points: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关联知识点(JSON数组)"
    )
    source_resource_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("resources.id"), nullable=True, comment="来源资源ID"
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="来源链接(板书图/录播片段)"
    )
    subject: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="学科")
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否启用"
    )
    # v2 新增：教师推荐模型（用于负载均衡 sticky 策略优先匹配）
    recommended_model: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="推荐模型(如 deepseek-chat)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, comment="更新时间"
    )


class ClassroomRecord(Base):
    """课堂记录表 - 录播视频与板书的结构化记录"""

    __tablename__ = "classroom_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="记录ID")
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True, comment="租户ID"
    )
    classroom_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("classrooms.id"), nullable=False, index=True, comment="课堂ID"
    )
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id"), nullable=False, index=True, comment="课程ID"
    )
    record_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="类型: video/board_photo/transcript"
    )
    resource_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("resources.id"), nullable=True, comment="关联资源ID"
    )
    transcript: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="转录/OCR文本"
    )
    segments: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="分段时间戳文本(JSON)"
    )
    knowledge_points: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="覆盖知识点(JSON)"
    )
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False, comment="状态: pending/processing/ready/failed"
    )
    # v2 新增字段
    file_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="MinIO 文件路径"
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="OCR/ASR provider: aliyun/tencent/mock"
    )
    error_msg: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="失败时的错误信息"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="创建时间"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True, comment="更新时间"
    )

    def to_dict(self) -> dict:
        """转为字典"""
        import json
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "classroom_id": self.classroom_id,
            "course_id": self.course_id,
            "record_type": self.record_type,
            "resource_id": self.resource_id,
            "transcript": self.transcript,
            "segments": json.loads(self.segments) if self.segments else None,
            "knowledge_points": json.loads(self.knowledge_points) if self.knowledge_points else None,
            "status": self.status,
            "file_url": self.file_url,
            "provider": self.provider,
            "error_msg": self.error_msg,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
