"""
智慧学伴 资源管理 Service
处理文件上传(MinIO+DB)、资源列表、关联知识点、AI标签、AI摘要等业务逻辑
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.resource import Resource
from app.repositories.resource_repo import ResourceRepository
from app.schemas.common import PaginationParams, PaginatedResponse
from app.services.file_parser import FileParser
from app.services.search_service import search_service

logger = logging.getLogger(__name__)


class ResourceService:
    """资源管理服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ResourceRepository(db)

    # ==================== MinIO 操作 ====================

    def _get_minio_client(self):
        """获取 MinIO 客户端"""
        try:
            from minio import Minio

            client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            # 确保 Bucket 存在
            if not client.bucket_exists(settings.MINIO_BUCKET):
                client.make_bucket(settings.MINIO_BUCKET)
            return client
        except Exception as e:
            logger.error(f"MinIO 连接失败: {e}")
            return None

    async def _upload_to_minio(self, file_data: bytes, file_key: str, content_type: str) -> Optional[str]:
        """
        上传文件到 MinIO

        Args:
            file_data: 文件二进制数据
            file_key: 存储Key
            content_type: MIME 类型

        Returns:
            文件访问URL或None
        """
        client = self._get_minio_client()
        if client is None:
            return None

        try:
            from io import BytesIO

            client.put_object(
                settings.MINIO_BUCKET,
                file_key,
                BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
            )
            return file_key
        except Exception as e:
            logger.error(f"MinIO 上传失败: {e}")
            return None

    async def _get_presigned_url(self, file_key: str, expires_hours: int = 1) -> Optional[str]:
        """
        获取 MinIO 预签名URL

        使用 MINIO_PUBLIC_ENDPOINT（浏览器可访问地址）创建 MinIO client，
        以保证返回给前端的预签名 URL 能被浏览器正常解析与访问。
        若 MINIO_PUBLIC_ENDPOINT 未配置，则回退到 MINIO_ENDPOINT。
        上传操作仍走 _get_minio_client（使用内网 MINIO_ENDPOINT）。

        Args:
            file_key: 存储Key
            expires_hours: 过期时间（小时）

        Returns:
            预签名URL
        """
        try:
            from datetime import timedelta

            from minio import Minio

            # 使用公网 endpoint 生成预签名 URL，供浏览器访问
            client = Minio(
                settings.MINIO_PUBLIC_ENDPOINT_OR_DEFAULT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )

            url = client.presigned_get_object(
                settings.MINIO_BUCKET,
                file_key,
                expires=timedelta(hours=expires_hours),
            )
            return url
        except Exception as e:
            logger.error(f"获取预签名URL失败: {e}")
            return None

    # ==================== 业务操作 ====================

    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        uploader_id: int,
        tenant_id: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        resource_type: Optional[str] = None,
        course_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        上传文件（MinIO + DB）

        Args:
            file_data: 文件二进制数据
            filename: 原始文件名
            content_type: MIME类型
            uploader_id: 上传者ID
            tenant_id: 租户ID
            title: 资源标题
            description: 资源描述
            resource_type: 资源类型
            course_id: 关联课程ID

        Returns:
            资源信息
        """
        # 自动推断资源类型
        if not resource_type:
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "other"
            type_map = {
                "pdf": "pdf", "docx": "docx", "doc": "docx",
                "txt": "txt", "md": "txt", "rtf": "txt",
                "pptx": "pptx", "ppt": "pptx",
                "mp4": "video", "avi": "video", "mov": "video",
                "mp3": "audio", "wav": "audio",
                "jpg": "image", "jpeg": "image", "png": "image", "gif": "image", "webp": "image",
            }
            resource_type = type_map.get(ext, "other")

        # 生成存储Key
        date_prefix = datetime.utcnow().strftime("%Y/%m/%d")
        file_key = f"resources/{date_prefix}/{uuid.uuid4().hex}/{filename}"

        # 上传到 MinIO
        minio_key = await self._upload_to_minio(file_data, file_key, content_type)

        # 解析文件内容
        parsed_text = ""
        try:
            parsed_text = await FileParser.parse_file(
                file_data, mime_type=content_type, filename=filename
            )
        except Exception as e:
            logger.warning(f"文件解析失败: {e}")

        # 创建数据库记录
        resource_data = {
            "title": title or filename,
            "description": description or "",
            "resource_type": resource_type,
            "mime_type": content_type,
            "file_size": len(file_data),
            "file_key": minio_key,
            "tenant_id": tenant_id or 0,
            "uploader_id": uploader_id,
            "course_id": course_id,
            "is_public": False,
            "is_active": True,
        }

        if parsed_text:
            resource_data["metadata_json"] = json.dumps(
                {"parsed_text_preview": parsed_text[:500], "parsed_text_length": len(parsed_text)},
                ensure_ascii=False,
            )

        resource = await self.repo.create(resource_data)

        # 异步索引到搜索引擎
        try:
            await search_service.index_document(
                str(resource.id),
                {
                    "id": resource.id,
                    "title": resource.title,
                    "content": parsed_text[:5000] if parsed_text else "",
                    "description": resource.description or "",
                    "doc_type": "resource",
                    "resource_type": resource.resource_type,
                    "tenant_id": resource.tenant_id,
                    "uploader_id": resource.uploader_id,
                    "course_id": resource.course_id,
                    "is_public": resource.is_public,
                    "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
                },
            )
        except Exception as e:
            logger.warning(f"资源索引失败: {e}")

        return {
            "id": resource.id,
            "tenant_id": resource.tenant_id,
            "title": resource.title,
            "resource_type": resource.resource_type,
            "file_size": resource.file_size,
            "file_key": resource.file_key,
            "created_at": resource.created_at.isoformat() if resource.created_at else None,
        }

    async def create_link_resource(
        self,
        url: str,
        title: str,
        uploader_id: int,
        tenant_id: Optional[int],
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a web-link resource without uploading a file."""
        resource = await self.repo.create(
            {
                "title": title,
                "description": description or "",
                "resource_type": "link",
                "mime_type": "text/uri-list",
                "url": url,
                "tenant_id": tenant_id or 0,
                "uploader_id": uploader_id,
                "is_public": False,
                "is_active": True,
            }
        )
        return await self.get_resource_detail(resource.id) or {"id": resource.id, "title": title, "url": url}

    async def list_resources(
        self,
        pagination: PaginationParams,
        resource_type: Optional[str] = None,
        uploader_id: Optional[int] = None,
        search: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> PaginatedResponse:
        """获取资源列表"""
        items, total = await self.repo.list_active_resources(
            pagination,
            resource_type=resource_type,
            uploader_id=uploader_id,
            search=search,
            tenant_id=tenant_id,
        )

        resource_list = [
            {
                "id": r.id,
                "title": r.title,
                "description": r.description,
                "resource_type": r.resource_type,
                "file_size": r.file_size,
                "mime_type": r.mime_type,
                "thumbnail_url": r.thumbnail_url,
                "tags": json.loads(r.tags) if r.tags else [],
                "download_count": r.download_count,
                "view_count": r.view_count,
                "is_public": r.is_public,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            }
            for r in items
        ]

        return PaginatedResponse(
            items=resource_list,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_resource_detail(self, resource_id: int) -> Optional[Dict[str, Any]]:
        """获取资源详情"""
        resource = await self.repo.get_by_id(resource_id)
        if not resource or resource.deleted_at:
            return None

        # 获取预签名URL
        preview_url = None
        if resource.file_key:
            preview_url = await self._get_presigned_url(resource.file_key)

        metadata = {}
        if resource.metadata_json:
            try:
                metadata = json.loads(resource.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": resource.id,
            "tenant_id": resource.tenant_id,
            "title": resource.title,
            "description": resource.description,
            "resource_type": resource.resource_type,
            "mime_type": resource.mime_type,
            "file_size": resource.file_size,
            "file_key": resource.file_key,
            "url": resource.url,
            "thumbnail_url": resource.thumbnail_url,
            "preview_url": preview_url,
            "course_id": resource.course_id,
            "uploader_id": resource.uploader_id,
            "download_count": resource.download_count,
            "view_count": resource.view_count,
            "tags": json.loads(resource.tags) if resource.tags else [],
            "metadata": metadata,
            "is_public": resource.is_public,
            "created_at": resource.created_at.isoformat() if resource.created_at else None,
            "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
        }

    async def delete_resource(self, resource_id: int) -> bool:
        """软删除资源"""
        resource = await self.repo.soft_delete(resource_id)
        return resource is not None

    async def update_resource(self, resource_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """更新资源信息"""
        resource = await self.repo.update(resource_id, update_data)
        if not resource:
            return None

        return {
            "id": resource.id,
            "title": resource.title,
            "description": resource.description,
            "tags": json.loads(resource.tags) if resource.tags else [],
            "updated_at": resource.updated_at.isoformat() if resource.updated_at else None,
        }

    async def link_to_node(self, resource_id: int, node_id: str) -> bool:
        """关联资源到知识节点"""
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            return False

        # 更新 metadata_json 中的关联节点列表
        metadata = {}
        if resource.metadata_json:
            try:
                metadata = json.loads(resource.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        linked_nodes = metadata.get("linked_nodes", [])
        if node_id not in linked_nodes:
            linked_nodes.append(node_id)
            metadata["linked_nodes"] = linked_nodes
            await self.repo.update(resource_id, {"metadata_json": json.dumps(metadata, ensure_ascii=False)})

        # Keep the Neo4j projection in sync so graph detail queries can see it.
        from app.services.graph_service import graph_service

        detail = await self.get_resource_detail(resource_id)
        if detail:
            await graph_service.link_resource(node_id, detail)

        return True

    async def unlink_from_node(self, resource_id: int, node_id: str) -> bool:
        """取消关联资源到知识节点"""
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            return False

        metadata = {}
        if resource.metadata_json:
            try:
                metadata = json.loads(resource.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        linked_nodes = metadata.get("linked_nodes", [])
        if node_id in linked_nodes:
            linked_nodes.remove(node_id)
            metadata["linked_nodes"] = linked_nodes
            await self.repo.update(resource_id, {"metadata_json": json.dumps(metadata, ensure_ascii=False)})

        from app.services.graph_service import graph_service

        await graph_service.unlink_resource(node_id, resource_id)

        return True

    async def auto_tag(self, resource_id: int) -> List[str]:
        """
        AI 自动标签：基于资源标题和描述生成标签
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundException(message="资源不存在")

        # 从 metadata 获取解析文本
        metadata = {}
        if resource.metadata_json:
            try:
                metadata = json.loads(resource.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        # 简单关键词提取（生产环境应调用 AI）
        import re

        text = f"{resource.title or ''} {resource.description or ''}"
        text += f" {metadata.get('parsed_text_preview', '')}"

        # 基于规则的标签提取
        tag_rules = {
            "数学": ["数学", "函数", "方程", "微积分", "线性代数", "概率"],
            "物理": ["物理", "力学", "电磁", "光学", "热学", "量子"],
            "化学": ["化学", "有机", "无机", "反应", "分子"],
            "计算机": ["编程", "算法", "数据结构", "网络", "操作系统"],
            "英语": ["英语", "语法", "词汇", "阅读", "写作"],
        }

        tags = []
        for tag, keywords in tag_rules.items():
            if any(kw in text for kw in keywords):
                tags.append(tag)

        if not tags:
            tags = [resource.resource_type]

        # 更新到数据库
        await self.repo.update(resource_id, {"tags": json.dumps(tags, ensure_ascii=False)})

        return tags

    async def generate_summary(self, resource_id: int) -> str:
        """
        AI 生成摘要
        """
        resource = await self.repo.get_by_id(resource_id)
        if not resource:
            raise NotFoundException(message="资源不存在")

        metadata = {}
        if resource.metadata_json:
            try:
                metadata = json.loads(resource.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        parsed_text = metadata.get("parsed_text_preview", "")
        if not parsed_text:
            return "无法生成摘要：文件内容为空"

        # 调用 OpenAI 生成摘要
        try:
            import httpx

            url = f"{settings.OPENAI_API_BASE}/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": "你是一个教育资源摘要助手。请为以下内容生成简洁的中文摘要，不超过200字。"},
                    {"role": "user", "content": parsed_text[:3000]},
                ],
                "max_tokens": 300,
                "temperature": 0.3,
            }

            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                summary = data["choices"][0]["message"]["content"]

            # 保存到 metadata
            metadata["ai_summary"] = summary
            await self.repo.update(resource_id, {"metadata_json": json.dumps(metadata, ensure_ascii=False)})

            return summary
        except Exception as e:
            logger.error(f"AI 摘要生成失败: {e}")
            return f"摘要生成失败: {str(e)}"
