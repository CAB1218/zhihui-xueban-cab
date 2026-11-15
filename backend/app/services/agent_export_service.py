"""
智慧学伴 对话导出服务
支持将 AI 会话导出为 Markdown / PDF 格式，上传到 MinIO 并生成预签名下载 URL。

导出流程:
1. 从 DB 读取 AgentSession + AgentMessage 列表
2. 拼装 Markdown 全文（含会话标题、元信息、逐条消息）
3. 若 format=pdf，用 reportlab 渲染 PDF
4. 上传到 MinIO exports bucket
5. 生成预签名 URL（有效期由 settings.EXPORT_PRESIGN_EXPIRE 控制）
"""
import io
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import AgentMessage, AgentSession
from app.models.export import AgentExport

logger = logging.getLogger(__name__)


class AgentExportService:
    """对话导出服务 — 封装 Markdown/PDF 生成 + MinIO 上传 + 预签名 URL"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ============ 公开方法 ============

    async def create_export_record(
        self,
        session_id: int,
        tenant_id: int,
        user_id: int,
        export_format: str,
    ) -> AgentExport:
        """创建导出记录（status=pending）

        Args:
            session_id: 会话 ID
            tenant_id: 租户 ID
            user_id: 用户 ID
            export_format: 导出格式 (pdf / markdown)

        Returns:
            新建的 AgentExport ORM 对象
        """
        export_record = AgentExport(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            export_format=export_format,
            status="pending",
        )
        self.db.add(export_record)
        await self.db.flush()
        return export_record

    async def generate_and_upload(
        self,
        export_id: int,
    ) -> AgentExport:
        """执行导出：生成文件 → 上传 MinIO → 更新记录状态（异步包装）

        此方法为 async 接口的包装器，内部调用同步实现。

        Args:
            export_id: AgentExport 记录 ID

        Returns:
            更新后的 AgentExport 对象

        Raises:
            ValueError: 导出记录不存在或会话无消息
        """
        return self.generate_and_upload_sync(export_id)

    def generate_and_upload_sync(
        self,
        export_id: int,
    ) -> AgentExport:
        """执行导出（同步实现，供 Celery worker 调用）

        生成文件 → 上传 MinIO → 更新记录状态

        Args:
            export_id: AgentExport 记录 ID

        Returns:
            更新后的 AgentExport 对象

        Raises:
            ValueError: 导出记录不存在或会话无消息
        """
        from app.core.celery_app import get_sync_session

        # 使用同步 session（Celery worker 是同步进程）
        with get_sync_session() as sync_db:
            # 读取导出记录
            export_record = sync_db.execute(
                select(AgentExport).where(AgentExport.id == export_id)
            ).scalars().first()

            if not export_record:
                raise ValueError(f"导出记录 {export_id} 不存在")

            try:
                export_record.status = "processing"
                sync_db.commit()
                sync_db.refresh(export_record)

                # 读取会话和消息
                session = sync_db.execute(
                    select(AgentSession).where(AgentSession.id == export_record.session_id)
                ).scalars().first()

                if not session:
                    export_record.status = "failed"
                    export_record.error_msg = f"会话 {export_record.session_id} 不存在"
                    sync_db.commit()
                    return export_record

                messages_result = sync_db.execute(
                    select(AgentMessage)
                    .where(AgentMessage.session_id == export_record.session_id)
                    .order_by(AgentMessage.created_at)
                )
                messages = messages_result.scalars().all()

                if not messages:
                    export_record.status = "failed"
                    export_record.error_msg = "会话没有消息，无法导出"
                    sync_db.commit()
                    return export_record

                # 生成文件内容
                file_data: bytes
                content_type: str
                file_ext: str

                if export_record.export_format == "pdf":
                    file_data = self._generate_pdf(session, messages)
                    content_type = "application/pdf"
                    file_ext = "pdf"
                else:
                    file_data = self._generate_markdown(session, messages)
                    content_type = "text/markdown"
                    file_ext = "md"

                # 上传到 MinIO
                file_key = (
                    f"exports/{export_record.tenant_id}/"
                    f"{export_record.session_id}/{uuid.uuid4().hex}.{file_ext}"
                )

                self._upload_to_minio(file_data, file_key, content_type)

                # 更新记录
                export_record.status = "completed"
                export_record.file_key = file_key
                export_record.file_size = len(file_data)
                export_record.completed_at = datetime.utcnow()
                export_record.expired_at = datetime.utcnow() + timedelta(
                    seconds=settings.EXPORT_PRESIGN_EXPIRE
                )
                sync_db.commit()
                sync_db.refresh(export_record)

                logger.info(
                    "导出完成: export_id=%s, format=%s, size=%d bytes",
                    export_id,
                    export_record.export_format,
                    len(file_data),
                )
                return export_record

            except Exception as e:
                logger.error("导出失败 export_id=%s: %s", export_id, e, exc_info=True)
                # 回滚后重新设置失败状态
                sync_db.rollback()
                export_record = sync_db.execute(
                    select(AgentExport).where(AgentExport.id == export_id)
                ).scalars().first()
                if export_record:
                    export_record.status = "failed"
                    export_record.error_msg = str(e)[:500]
                    sync_db.commit()
                    sync_db.refresh(export_record)
                return export_record

    async def get_download_url(self, export_id: int, tenant_id: int) -> Tuple[str, datetime]:
        """生成预签名下载 URL

        Args:
            export_id: 导出记录 ID
            tenant_id: 租户 ID（用于权限校验）

        Returns:
            (download_url, expired_at)

        Raises:
            ValueError: 导出记录不存在/未完成/不属于该租户
        """
        stmt = select(AgentExport).where(
            AgentExport.id == export_id,
            AgentExport.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        export_record = result.scalars().first()

        if not export_record:
            raise ValueError("导出记录不存在")
        if export_record.status != "completed":
            raise ValueError(f"导出未完成，当前状态: {export_record.status}")
        if not export_record.file_key:
            raise ValueError("导出文件不存在")

        # 生成预签名 URL
        download_url = self._get_presigned_url(export_record.file_key)
        expired_at = datetime.utcnow() + timedelta(seconds=settings.EXPORT_PRESIGN_EXPIRE)

        return download_url, expired_at

    # ============ 文件生成 ============

    def _generate_markdown(
        self, session: AgentSession, messages: List[AgentMessage]
    ) -> bytes:
        """生成 Markdown 格式的导出文件

        Args:
            session: 会话对象
            messages: 消息列表（按时间排序）

        Returns:
            UTF-8 编码的 Markdown 文本字节
        """
        lines: List[str] = []

        # 标题
        lines.append(f"# {session.title or 'AI 对话记录'}")
        lines.append("")

        # 元信息
        lines.append("## 会话信息")
        lines.append("")
        lines.append(f"- **智能体类型**: {session.agent_type}")
        if session.scene_type:
            lines.append(f"- **场景类型**: {session.scene_type}")
        lines.append(f"- **使用模型**: {session.model_name or '未知'}")
        lines.append(f"- **消息数量**: {session.message_count}")
        lines.append(f"- **总 Token 消耗**: {session.total_tokens}")
        if session.created_at:
            lines.append(
                f"- **创建时间**: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        if session.last_message_at:
            lines.append(
                f"- **最后消息**: {session.last_message_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        lines.append("")
        lines.append("---")
        lines.append("")

        # 逐条消息
        lines.append("## 对话内容")
        lines.append("")

        for msg in messages:
            role_label = self._role_label(msg.role)
            timestamp = ""
            if msg.created_at:
                timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")

            lines.append(f"### {role_label}")
            lines.append(f"*{timestamp}*")
            if msg.model_name:
                lines.append(f"*模型: {msg.model_name}*")
            lines.append("")
            lines.append(msg.content or "")
            lines.append("")

            # 如果有 metadata（引用来源等）
            if msg.metadata_json:
                try:
                    metadata = json.loads(msg.metadata_json)
                    citations = metadata.get("citations", [])
                    if citations:
                        lines.append("**引用来源:**")
                        for cite in citations:
                            title = cite.get("title", "")
                            source_url = cite.get("source_url", "")
                            cite_type = cite.get("type", "")
                            lines.append(f"- [{title}]({source_url}) ({cite_type})")
                        lines.append("")
                except (json.JSONDecodeError, TypeError):
                    pass

            lines.append("---")
            lines.append("")

        # 页脚
        lines.append(f"*导出时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC*")

        content = "\n".join(lines)
        return content.encode("utf-8")

    def _generate_pdf(
        self, session: AgentSession, messages: List[AgentMessage]
    ) -> bytes:
        """生成 PDF 格式的导出文件

        使用 reportlab 渲染，支持中文内容。
        若 reportlab 未安装，回退为 Markdown 纯文本。

        Args:
            session: 会话对象
            messages: 消息列表

        Returns:
            PDF 文件字节
        """
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
            )

            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=20 * mm,
                leftMargin=20 * mm,
                topMargin=20 * mm,
                bottomMargin=20 * mm,
            )
            styles = getSampleStyleSheet()

            # 自定义样式
            title_style = ParagraphStyle(
                "ExportTitle",
                parent=styles["Title"],
                fontSize=18,
                spaceAfter=12,
            )
            meta_style = ParagraphStyle(
                "ExportMeta",
                parent=styles["Normal"],
                fontSize=10,
                textColor="#666666",
                spaceAfter=4,
            )
            role_style = ParagraphStyle(
                "RoleHeader",
                parent=styles["Heading3"],
                fontSize=13,
                textColor="#1976D2",
                spaceBefore=12,
                spaceAfter=4,
            )
            body_style = ParagraphStyle(
                "ExportBody",
                parent=styles["Normal"],
                fontSize=11,
                leading=16,
                spaceAfter=6,
            )
            citation_style = ParagraphStyle(
                "Citation",
                parent=styles["Normal"],
                fontSize=9,
                textColor="#888888",
                spaceAfter=2,
            )

            elements: list = []

            # 标题
            title = session.title or "AI 对话记录"
            elements.append(Paragraph(self._escape_xml(title), title_style))
            elements.append(Spacer(1, 8))

            # 元信息
            elements.append(
                Paragraph(
                    f"智能体类型: {session.agent_type} | 模型: {session.model_name or '未知'}",
                    meta_style,
                )
            )
            if session.scene_type:
                elements.append(Paragraph(f"场景: {session.scene_type}", meta_style))
            elements.append(
                Paragraph(
                    f"消息数: {session.message_count} | Token: {session.total_tokens}",
                    meta_style,
                )
            )
            if session.created_at:
                elements.append(
                    Paragraph(
                        f"创建时间: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
                        meta_style,
                    )
                )
            elements.append(Spacer(1, 12))

            # 逐条消息
            for msg in messages:
                role_label = self._role_label(msg.role)
                elements.append(Paragraph(role_label, role_style))

                timestamp = ""
                if msg.created_at:
                    timestamp = msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
                if msg.model_name:
                    elements.append(
                        Paragraph(
                            f"{timestamp} | 模型: {msg.model_name}",
                            meta_style,
                        )
                    )
                elif timestamp:
                    elements.append(Paragraph(timestamp, meta_style))

                # 消息内容（按段落分割）
                content = msg.content or ""
                for paragraph in content.split("\n"):
                    if paragraph.strip():
                        safe = self._escape_xml(paragraph)
                        elements.append(Paragraph(safe, body_style))

                # 引用来源
                if msg.metadata_json:
                    try:
                        metadata = json.loads(msg.metadata_json)
                        citations = metadata.get("citations", [])
                        if citations:
                            elements.append(Paragraph("引用来源:", citation_style))
                            for cite in citations:
                                cite_text = (
                                    f"- [{cite.get('title', '')}] "
                                    f"({cite.get('source_url', '')})"
                                )
                                elements.append(
                                    Paragraph(self._escape_xml(cite_text), citation_style)
                                )
                    except (json.JSONDecodeError, TypeError):
                        pass

                elements.append(Spacer(1, 8))

            # 页脚
            elements.append(Spacer(1, 20))
            elements.append(
                Paragraph(
                    f"导出时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                    meta_style,
                )
            )

            doc.build(elements)
            return buffer.getvalue()

        except ImportError:
            logger.warning("reportlab 未安装，PDF 导出回退为 Markdown 纯文本")
            return self._generate_markdown(session, messages)

    # ============ MinIO 操作 ============

    def _upload_to_minio(self, file_data: bytes, file_key: str, content_type: str) -> None:
        """上传文件到 MinIO exports bucket

        Args:
            file_data: 文件二进制数据
            file_key: MinIO 存储 Key
            content_type: MIME 类型
        """
        from io import BytesIO

        from minio import Minio

        client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        bucket = settings.EXPORT_MINIO_BUCKET
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        client.put_object(
            bucket,
            file_key,
            BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )

    def _get_presigned_url(self, file_key: str) -> str:
        """生成 MinIO 预签名下载 URL

        使用 MINIO_PUBLIC_ENDPOINT（浏览器可访问地址）创建 MinIO client，
        以保证返回给前端的预签名 URL 能被浏览器正常解析与访问。
        若 MINIO_PUBLIC_ENDPOINT 未配置，则回退到 MINIO_ENDPOINT。

        Args:
            file_key: MinIO 存储 Key

        Returns:
            预签名 URL 字符串
        """
        from minio import Minio

        client = Minio(
            settings.MINIO_PUBLIC_ENDPOINT_OR_DEFAULT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        bucket = settings.EXPORT_MINIO_BUCKET
        url = client.presigned_get_object(
            bucket,
            file_key,
            expires=timedelta(seconds=settings.EXPORT_PRESIGN_EXPIRE),
        )
        return url

    # ============ 辅助方法 ============

    @staticmethod
    def _role_label(role: str) -> str:
        """将 role 转为可读标签"""
        labels = {
            "user": "用户",
            "assistant": "AI 助手",
            "system": "系统",
        }
        return labels.get(role, role)

    @staticmethod
    def _escape_xml(text: str) -> str:
        """转义 XML 特殊字符（reportlab Paragraph 需要）"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )


# 全局实例工厂（用于依赖注入）
def get_agent_export_service(db: AsyncSession) -> AgentExportService:
    """获取 AgentExportService 实例

    Args:
        db: 异步数据库会话

    Returns:
        AgentExportService 实例
    """
    return AgentExportService(db)
