"""
智慧学伴 笔记服务
CRUD、AI增强（调用agent）、版本管理、分享、E2E加密笔记支持
"""
import json
import logging
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.encryption import decrypt_field, encrypt_field
from app.core.exceptions import NotFoundException, PermissionDeniedException, ValidationException
from app.models.note import Note, NoteVersion
from app.schemas.common import PaginatedResponse, PaginationParams

logger = logging.getLogger(__name__)


class NoteService:
    """笔记服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_note(
        self,
        tenant_id: int,
        owner_id: int,
        title: str,
        content: Optional[str] = None,
        content_plain: Optional[str] = None,
        note_type: str = "personal",
        course_id: Optional[int] = None,
        resource_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        is_encrypted: bool = False,
    ) -> Dict[str, Any]:
        """
        创建笔记

        Args:
            tenant_id: 租户ID
            owner_id: 所有者ID
            title: 笔记标题
            content: 笔记内容
            content_plain: 纯文本内容
            note_type: 笔记类型
            course_id: 关联课程ID
            resource_id: 关联资源ID
            tags: 标签列表
            is_encrypted: 是否启用E2E加密

        Returns:
            创建的笔记信息
        """
        # E2E加密处理
        stored_content = content
        if is_encrypted and content:
            stored_content = encrypt_field(content)

        # 计算字数
        word_count = len(content_plain) if content_plain else (len(content) if content else 0)

        note = Note(
            tenant_id=tenant_id,
            title=title,
            content=stored_content,
            content_plain=content_plain,
            note_type=note_type,
            course_id=course_id,
            resource_id=resource_id,
            owner_id=owner_id,
            tags=json.dumps(tags or [], ensure_ascii=False),
            word_count=word_count,
            version=1,
            is_deleted=False,
        )
        self.db.add(note)
        await self.db.flush()

        # 创建第一个版本记录
        version = NoteVersion(
            note_id=note.id,
            version=1,
            title=title,
            content=stored_content,
            change_summary="创建笔记",
            created_by=owner_id,
        )
        self.db.add(version)
        await self.db.flush()

        return self._note_to_dict(note, is_encrypted=is_encrypted)

    async def get_note(
        self,
        note_id: int,
        tenant_id: int,
        user_id: int,
        is_encrypted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        获取笔记详情

        Args:
            note_id: 笔记ID
            tenant_id: 租户ID
            user_id: 用户ID
            is_encrypted: 是否为加密笔记

        Returns:
            笔记信息
        """
        stmt = select(Note).where(
            and_(
                Note.id == note_id,
                Note.tenant_id == tenant_id,
                Note.is_deleted == False,
            )
        )
        result = await self.db.execute(stmt)
        note = result.scalars().first()

        if not note:
            return None

        return self._note_to_dict(note, is_encrypted=is_encrypted)

    async def list_notes(
        self,
        tenant_id: int,
        owner_id: int,
        pagination: PaginationParams,
        course_id: Optional[int] = None,
        note_type: Optional[str] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse:
        """
        获取笔记列表

        Args:
            tenant_id: 租户ID
            owner_id: 所有者ID
            pagination: 分页参数
            course_id: 课程ID筛选
            note_type: 笔记类型筛选
            search: 搜索关键词

        Returns:
            分页笔记列表
        """
        conditions = [
            Note.tenant_id == tenant_id,
            Note.owner_id == owner_id,
            Note.is_deleted == False,
        ]

        if course_id:
            conditions.append(Note.course_id == course_id)
        if note_type:
            conditions.append(Note.note_type == note_type)
        if search:
            conditions.append(Note.title.ilike(f"%{search}%"))

        # 查询总数
        count_stmt = select(func.count(Note.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 查询数据
        stmt = (
            select(Note)
            .where(and_(*conditions))
            .order_by(desc(Note.updated_at))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        result = await self.db.execute(stmt)
        notes = result.scalars().all()

        items = [self._note_to_dict(note) for note in notes]

        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def update_note(
        self,
        note_id: int,
        tenant_id: int,
        user_id: int,
        title: Optional[str] = None,
        content: Optional[str] = None,
        content_plain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        change_summary: Optional[str] = None,
        is_encrypted: bool = False,
        bypass_owner_check: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        更新笔记

        Args:
            note_id: 笔记ID
            tenant_id: 租户ID
            user_id: 用户ID
            title: 新标题
            content: 新内容
            content_plain: 新纯文本内容
            tags: 新标签
            change_summary: 变更摘要
            is_encrypted: 是否为加密笔记

        Returns:
            更新后的笔记信息
        """
        stmt = select(Note).where(
            and_(
                Note.id == note_id,
                Note.tenant_id == tenant_id,
                Note.is_deleted == False,
            )
        )
        result = await self.db.execute(stmt)
        note = result.scalars().first()

        if not note:
            return None

        if note.owner_id != user_id and not bypass_owner_check:
            raise PermissionDeniedException(message="只能修改自己的笔记")

        # 准备更新数据
        update_data: Dict[str, Any] = {}
        stored_content = content

        if title is not None:
            update_data["title"] = title
        if content is not None:
            if is_encrypted:
                stored_content = encrypt_field(content)
            update_data["content"] = stored_content
        if content_plain is not None:
            update_data["content_plain"] = content_plain
            update_data["word_count"] = len(content_plain)
        if tags is not None:
            update_data["tags"] = json.dumps(tags, ensure_ascii=False)

        if update_data:
            # 版本号+1
            new_version = note.version + 1
            update_data["version"] = new_version

            # 执行更新
            for key, value in update_data.items():
                setattr(note, key, value)

            # 创建版本记录
            version = NoteVersion(
                note_id=note.id,
                version=new_version,
                title=title or note.title,
                content=stored_content or note.content,
                change_summary=change_summary or f"更新至版本{new_version}",
                created_by=user_id,
            )
            self.db.add(version)
            await self.db.flush()

        return self._note_to_dict(note, is_encrypted=is_encrypted)

    async def delete_note(
        self,
        note_id: int,
        tenant_id: int,
        user_id: int,
        bypass_owner_check: bool = False,
    ) -> bool:
        """
        软删除笔记

        Args:
            note_id: 笔记ID
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        stmt = select(Note).where(
            and_(
                Note.id == note_id,
                Note.tenant_id == tenant_id,
                Note.is_deleted == False,
            )
        )
        result = await self.db.execute(stmt)
        note = result.scalars().first()

        if not note:
            return False

        if note.owner_id != user_id and not bypass_owner_check:
            raise PermissionDeniedException(message="只能删除自己的笔记")

        note.is_deleted = True
        note.deleted_at = datetime.utcnow()
        await self.db.flush()

        return True

    async def ai_enhance(
        self,
        note_id: int,
        tenant_id: int,
        user_id: int,
        enhance_type: str = "summary",
        additional_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        AI增强笔记

        Args:
            note_id: 笔记ID
            tenant_id: 租户ID
            user_id: 用户ID
            enhance_type: 增强类型 summary/correct/expand/mindmap
            additional_instructions: 额外指令

        Returns:
            增强后的内容
        """
        note_data = await self.get_note(note_id, tenant_id, user_id)
        if not note_data:
            raise NotFoundException(message="笔记不存在")

        content = note_data.get("content", "")
        if not content:
            raise ValidationException(message="笔记内容为空，无法增强")

        # 构建AI增强提示
        type_instructions = {
            "summary": "请为以下笔记内容生成简洁的摘要，保留核心知识点。",
            "correct": "请检查以下笔记内容中的错误，并给出纠正建议。",
            "expand": "请在以下笔记内容基础上，补充相关知识点的详细解释和拓展。",
            "mindmap": "请将以下笔记内容转换为思维导图格式（Markdown缩进表示层级）。",
        }

        instruction = type_instructions.get(enhance_type, type_instructions["summary"])
        if additional_instructions:
            instruction += f"\n额外要求：{additional_instructions}"

        # 调用LLM
        from app.agents.base import BaseAgent

        class _EnhanceAgent(BaseAgent):
            agent_type = "note_enhance"

            @property
            def system_prompt(self) -> str:
                return instruction

        agent = _EnhanceAgent()
        result = await agent.execute(
            messages=[{"role": "user", "content": content[:4000]}],
            context={"tenant_id": tenant_id, "user_id": user_id},
        )

        enhanced_content = result.get("content", "")

        # 标记笔记为AI增强
        stmt = select(Note).where(Note.id == note_id)
        db_result = await self.db.execute(stmt)
        note = db_result.scalars().first()
        if note:
            note.ai_enhanced = True
            await self.db.flush()

        return {
            "enhanced_content": enhanced_content,
            "enhance_type": enhance_type,
            "original_word_count": len(content),
            "enhanced_word_count": len(enhanced_content),
        }

    async def list_versions(
        self,
        note_id: int,
        tenant_id: int,
        user_id: int,
    ) -> List[Dict[str, Any]]:
        """
        获取笔记版本历史

        Args:
            note_id: 笔记ID
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            版本历史列表
        """
        # 验证笔记归属
        note_data = await self.get_note(note_id, tenant_id, user_id)
        if not note_data:
            raise NotFoundException(message="笔记不存在")

        stmt = (
            select(NoteVersion)
            .where(NoteVersion.note_id == note_id)
            .order_by(desc(NoteVersion.version))
        )
        result = await self.db.execute(stmt)
        versions = result.scalars().all()

        return [
            {
                "id": v.id,
                "note_id": v.note_id,
                "version": v.version,
                "title": v.title,
                "change_summary": v.change_summary,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ]

    async def share_note(
        self,
        note_id: int,
        tenant_id: int,
        user_id: int,
        bypass_owner_check: bool = False,
    ) -> Dict[str, Any]:
        """
        生成笔记分享链接

        Args:
            note_id: 笔记ID
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            分享信息
        """
        stmt = select(Note).where(
            and_(
                Note.id == note_id,
                Note.tenant_id == tenant_id,
                Note.is_deleted == False,
            )
        )
        result = await self.db.execute(stmt)
        note = result.scalars().first()

        if not note:
            raise NotFoundException(message="笔记不存在")

        if note.owner_id != user_id and not bypass_owner_check:
            raise PermissionDeniedException(message="只能分享自己的笔记")

        # 生成分享码
        share_code = secrets.token_urlsafe(16)
        note.share_code = share_code
        await self.db.flush()

        share_url = f"/notes/shared/{share_code}"

        return {
            "share_code": share_code,
            "share_url": share_url,
            "expires_at": None,
        }

    def _note_to_dict(
        self,
        note: Note,
        is_encrypted: bool = False,
    ) -> Dict[str, Any]:
        """将Note模型转换为字典"""
        content = note.content
        if is_encrypted and content:
            try:
                content = decrypt_field(content)
            except Exception:
                content = "[加密内容]"

        tags = []
        if note.tags:
            try:
                tags = json.loads(note.tags)
            except (json.JSONDecodeError, TypeError):
                tags = []

        return {
            "id": note.id,
            "tenant_id": note.tenant_id,
            "title": note.title,
            "content": content,
            "content_plain": note.content_plain,
            "note_type": note.note_type,
            "course_id": note.course_id,
            "resource_id": note.resource_id,
            "owner_id": note.owner_id,
            "tags": tags,
            "ai_enhanced": note.ai_enhanced,
            "share_code": note.share_code,
            "word_count": note.word_count,
            "version": note.version,
            "is_deleted": note.is_deleted,
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        }
