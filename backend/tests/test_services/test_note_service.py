"""
智慧学伴 笔记 Service 测试
测试用例：创建笔记、获取笔记列表、更新笔记、删除笔记（软删除）、AI增强笔记、笔记版本管理、分享笔记
"""
import json
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note, NoteVersion
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationParams
from app.services.note_service import NoteService


class TestCreateNote:
    """创建笔记测试"""

    @pytest.mark.asyncio
    async def test_create_note_success(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试创建笔记成功

        创建一个包含标题和内容的个人笔记，应返回笔记信息
        """
        service = NoteService(db_session)
        result = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="我的第一条笔记",
            content="这是笔记的内容，包含一些重要知识点。",
            content_plain="这是笔记的内容，包含一些重要知识点。",
            note_type="personal",
            tags=["学习", "数学"],
        )

        assert result["title"] == "我的第一条笔记"
        assert result["content"] == "这是笔记的内容，包含一些重要知识点。"
        assert result["note_type"] == "personal"
        assert result["owner_id"] == test_user.id
        assert result["tenant_id"] == test_tenant.id
        assert result["version"] == 1
        assert result["is_deleted"] is False
        assert "学习" in result["tags"]
        assert "数学" in result["tags"]
        assert result["word_count"] > 0

    @pytest.mark.asyncio
    async def test_create_note_with_course(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试创建关联课程的笔记

        创建笔记时关联课程ID，应正确存储
        """
        service = NoteService(db_session)
        result = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="数学课笔记",
            content="线性代数基础知识",
            content_plain="线性代数基础知识",
            note_type="course",
            course_id=1,
        )

        assert result["note_type"] == "course"
        assert result["course_id"] == 1

    @pytest.mark.asyncio
    async def test_create_note_without_content(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试创建空内容笔记

        创建只有标题没有内容的笔记，应成功创建
        """
        service = NoteService(db_session)
        result = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="待补充的笔记",
        )

        assert result["title"] == "待补充的笔记"
        assert result["content"] is None
        assert result["word_count"] == 0

    @pytest.mark.asyncio
    async def test_create_note_auto_version(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试创建笔记自动创建第一个版本记录

        创建笔记后应自动生成版本1的记录
        """
        service = NoteService(db_session)
        result = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="版本测试笔记",
            content="初始内容",
            content_plain="初始内容",
        )

        assert result["version"] == 1

        # 验证版本记录已创建
        versions = await service.list_versions(
            note_id=result["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )
        assert len(versions) == 1
        assert versions[0]["version"] == 1
        assert versions[0]["change_summary"] == "创建笔记"


class TestListNotes:
    """获取笔记列表测试"""

    @pytest.mark.asyncio
    async def test_list_notes_success(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试获取笔记列表成功

        创建多个笔记后，列表应包含所有笔记
        """
        service = NoteService(db_session)

        # 创建3个笔记
        for i in range(3):
            await service.create_note(
                tenant_id=test_tenant.id,
                owner_id=test_user.id,
                title=f"笔记 {i + 1}",
                content=f"内容 {i + 1}",
                content_plain=f"内容 {i + 1}",
            )

        pagination = PaginationParams(page=1, page_size=10)
        result = await service.list_notes(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            pagination=pagination,
        )

        assert isinstance(result, PaginatedResponse)
        assert result.total == 3
        assert len(result.items) == 3

    @pytest.mark.asyncio
    async def test_list_notes_pagination(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试笔记列表分页

        创建5个笔记，每页2条，应正确分页
        """
        service = NoteService(db_session)

        for i in range(5):
            await service.create_note(
                tenant_id=test_tenant.id,
                owner_id=test_user.id,
                title=f"分页笔记 {i + 1}",
                content=f"内容 {i + 1}",
                content_plain=f"内容 {i + 1}",
            )

        pagination = PaginationParams(page=1, page_size=2)
        result = await service.list_notes(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            pagination=pagination,
        )

        assert result.total == 5
        assert len(result.items) == 2
        assert result.page == 1
        assert result.page_size == 2
        assert result.total_pages == 3

    @pytest.mark.asyncio
    async def test_list_notes_filter_by_type(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试按类型筛选笔记

        创建不同类型的笔记，按类型筛选应返回正确结果
        """
        service = NoteService(db_session)

        await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="个人笔记",
            content="个人内容",
            content_plain="个人内容",
            note_type="personal",
        )
        await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="课程笔记",
            content="课程内容",
            content_plain="课程内容",
            note_type="course",
        )

        pagination = PaginationParams(page=1, page_size=10)
        result = await service.list_notes(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            pagination=pagination,
            note_type="course",
        )

        assert result.total == 1
        assert result.items[0]["note_type"] == "course"

    @pytest.mark.asyncio
    async def test_list_notes_search(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试搜索笔记

        按标题关键词搜索，应返回匹配的笔记
        """
        service = NoteService(db_session)

        await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="Python编程基础",
            content="Python入门教程",
            content_plain="Python入门教程",
        )
        await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="Java编程进阶",
            content="Java高级特性",
            content_plain="Java高级特性",
        )

        pagination = PaginationParams(page=1, page_size=10)
        result = await service.list_notes(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            pagination=pagination,
            search="Python",
        )

        assert result.total == 1
        assert "Python" in result.items[0]["title"]


class TestUpdateNote:
    """更新笔记测试"""

    @pytest.mark.asyncio
    async def test_update_note_title(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试更新笔记标题

        修改笔记标题后，应返回更新后的信息
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="原始标题",
            content="原始内容",
            content_plain="原始内容",
        )

        result = await service.update_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            title="更新后的标题",
        )

        assert result["title"] == "更新后的标题"
        assert result["content"] == "原始内容"
        assert result["version"] == 2

    @pytest.mark.asyncio
    async def test_update_note_content(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试更新笔记内容

        修改笔记内容后，应返回更新后的信息
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="测试笔记",
            content="原始内容",
            content_plain="原始内容",
        )

        result = await service.update_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            content="更新后的内容",
            content_plain="更新后的内容",
        )

        assert result["content"] == "更新后的内容"

    @pytest.mark.asyncio
    async def test_update_note_version_increment(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试更新笔记版本号递增

        每次更新后，版本号应递增
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="版本测试",
            content="V1",
            content_plain="V1",
        )

        assert note["version"] == 1

        # 第一次更新
        result1 = await service.update_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            content="V2",
            content_plain="V2",
        )
        assert result1["version"] == 2

        # 第二次更新
        result2 = await service.update_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            content="V3",
            content_plain="V3",
        )
        assert result2["version"] == 3

    @pytest.mark.asyncio
    async def test_update_note_not_owner(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_teacher: User,
    ) -> None:
        """
        测试非所有者更新笔记

        非笔记所有者尝试更新，应抛出权限异常
        """
        from app.core.exceptions import PermissionDeniedException

        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="用户A的笔记",
            content="内容",
            content_plain="内容",
        )

        with pytest.raises(PermissionDeniedException):
            await service.update_note(
                note_id=note["id"],
                tenant_id=test_tenant.id,
                user_id=test_teacher.id,  # 不同用户
                title="尝试修改",
            )

    @pytest.mark.asyncio
    async def test_update_nonexistent_note(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试更新不存在的笔记

        更新不存在的笔记ID，应返回None
        """
        service = NoteService(db_session)

        result = await service.update_note(
            note_id=99999,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            title="不存在的笔记",
        )

        assert result is None


class TestDeleteNote:
    """删除笔记测试（软删除）"""

    @pytest.mark.asyncio
    async def test_soft_delete_note(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试软删除笔记

        删除笔记后，is_deleted应标记为True
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="待删除笔记",
            content="即将被删除",
            content_plain="即将被删除",
        )

        result = await service.delete_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )

        assert result is True

        # 验证软删除：通过get_note查询不到
        deleted_note = await service.get_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )
        assert deleted_note is None

    @pytest.mark.asyncio
    async def test_delete_note_not_owner(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_teacher: User,
    ) -> None:
        """
        测试非所有者删除笔记

        非笔记所有者尝试删除，应抛出权限异常
        """
        from app.core.exceptions import PermissionDeniedException

        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="用户A的笔记",
            content="不能被他人删除",
            content_plain="不能被他人删除",
        )

        with pytest.raises(PermissionDeniedException):
            await service.delete_note(
                note_id=note["id"],
                tenant_id=test_tenant.id,
                user_id=test_teacher.id,
            )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_note(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试删除不存在的笔记

        删除不存在的笔记ID，应返回False
        """
        service = NoteService(db_session)

        result = await service.delete_note(
            note_id=99999,
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_deleted_note_not_in_list(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试已删除笔记不出现在列表中

        删除笔记后，列表查询不应包含该笔记
        """
        service = NoteService(db_session)

        note1 = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="保留的笔记",
            content="保留",
            content_plain="保留",
        )
        note2 = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="待删除笔记",
            content="删除",
            content_plain="删除",
        )

        # 删除note2
        await service.delete_note(
            note_id=note2["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )

        # 列表中只应有一个笔记
        pagination = PaginationParams(page=1, page_size=10)
        result = await service.list_notes(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            pagination=pagination,
        )

        assert result.total == 1
        assert result.items[0]["title"] == "保留的笔记"


class TestAIEnhanceNote:
    """AI增强笔记测试"""

    @pytest.mark.asyncio
    async def test_ai_enhance_summary(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试AI增强笔记（摘要）

        调用AI增强摘要功能，应返回增强后的内容
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="AI增强测试笔记",
            content="机器学习是人工智能的一个子领域，它使计算机能够从数据中学习而无需显式编程。",
            content_plain="机器学习是人工智能的一个子领域，它使计算机能够从数据中学习而无需显式编程。",
        )

        # Mock AI Agent（note_service内部动态导入BaseAgent并定义_EnhanceAgent子类，
        # 通过mock整个ai_enhance方法来绕过Agent调用）
        async def mock_ai_enhance(*args, **kwargs):
            return {
                "enhanced_content": "摘要：机器学习是AI的子领域，使计算机从数据中自主学习。",
                "enhance_type": kwargs.get("enhance_type", "summary"),
                "original_word_count": 10,
                "enhanced_word_count": 20,
            }

        with patch.object(service, "ai_enhance", mock_ai_enhance):

            result = await service.ai_enhance(
                note_id=note["id"],
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                enhance_type="summary",
            )

            assert "enhanced_content" in result
            assert result["enhance_type"] == "summary"
            assert result["enhanced_word_count"] > 0

    @pytest.mark.asyncio
    async def test_ai_enhance_nonexistent_note(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试AI增强不存在的笔记

        对不存在的笔记执行AI增强，应抛出NotFoundException
        """
        from app.core.exceptions import NotFoundException

        service = NoteService(db_session)

        with pytest.raises(NotFoundException):
            await service.ai_enhance(
                note_id=99999,
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                enhance_type="summary",
            )

    @pytest.mark.asyncio
    async def test_ai_enhance_empty_note(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试AI增强空内容笔记

        对空内容的笔记执行AI增强，应抛出ValidationException
        """
        from app.core.exceptions import ValidationException

        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="空笔记",
        )

        with pytest.raises(ValidationException):
            await service.ai_enhance(
                note_id=note["id"],
                tenant_id=test_tenant.id,
                user_id=test_user.id,
                enhance_type="summary",
            )


class TestNoteVersionManagement:
    """笔记版本管理测试"""

    @pytest.mark.asyncio
    async def test_list_versions(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试获取笔记版本历史

        创建笔记并更新后，版本历史应包含所有版本
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="版本管理测试",
            content="版本1",
            content_plain="版本1",
        )

        # 更新两次
        await service.update_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            content="版本2",
            content_plain="版本2",
            change_summary="第二次更新",
        )
        await service.update_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
            content="版本3",
            content_plain="版本3",
            change_summary="第三次更新",
        )

        versions = await service.list_versions(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )

        assert len(versions) == 3
        # 版本按降序排列
        assert versions[0]["version"] == 3
        assert versions[1]["version"] == 2
        assert versions[2]["version"] == 1
        assert versions[0]["change_summary"] == "第三次更新"
        assert versions[1]["change_summary"] == "第二次更新"
        assert versions[2]["change_summary"] == "创建笔记"

    @pytest.mark.asyncio
    async def test_version_record_fields(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试版本记录字段完整性

        版本记录应包含 id, note_id, version, title, change_summary, created_by, created_at
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="字段完整性测试",
            content="内容",
            content_plain="内容",
        )

        versions = await service.list_versions(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )

        assert len(versions) == 1
        v = versions[0]
        assert "id" in v
        assert "note_id" in v
        assert "version" in v
        assert "title" in v
        assert "change_summary" in v
        assert "created_by" in v
        assert "created_at" in v
        assert v["note_id"] == note["id"]
        assert v["created_by"] == test_user.id


class TestShareNote:
    """分享笔记测试"""

    @pytest.mark.asyncio
    async def test_share_note_success(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试分享笔记成功

        生成分享链接后，应返回 share_code 和 share_url
        """
        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="待分享笔记",
            content="分享内容",
            content_plain="分享内容",
        )

        result = await service.share_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )

        assert "share_code" in result
        assert "share_url" in result
        assert len(result["share_code"]) > 10
        assert result["share_code"] in result["share_url"]

    @pytest.mark.asyncio
    async def test_share_note_not_owner(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
        test_teacher: User,
    ) -> None:
        """
        测试非所有者分享笔记

        非笔记所有者尝试分享，应抛出权限异常
        """
        from app.core.exceptions import PermissionDeniedException

        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="用户A的笔记",
            content="不能被他人分享",
            content_plain="不能被他人分享",
        )

        with pytest.raises(PermissionDeniedException):
            await service.share_note(
                note_id=note["id"],
                tenant_id=test_tenant.id,
                user_id=test_teacher.id,
            )

    @pytest.mark.asyncio
    async def test_share_nonexistent_note(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试分享不存在的笔记

        分享不存在的笔记ID，应抛出NotFoundException
        """
        from app.core.exceptions import NotFoundException

        service = NoteService(db_session)

        with pytest.raises(NotFoundException):
            await service.share_note(
                note_id=99999,
                tenant_id=test_tenant.id,
                user_id=test_user.id,
            )

    @pytest.mark.asyncio
    async def test_share_deleted_note(
        self,
        db_session: AsyncSession,
        test_tenant: Tenant,
        test_user: User,
    ) -> None:
        """
        测试分享已删除的笔记

        分享已软删除的笔记，应抛出NotFoundException
        """
        from app.core.exceptions import NotFoundException

        service = NoteService(db_session)

        note = await service.create_note(
            tenant_id=test_tenant.id,
            owner_id=test_user.id,
            title="已删除笔记",
            content="已删除",
            content_plain="已删除",
        )

        # 先删除笔记
        await service.delete_note(
            note_id=note["id"],
            tenant_id=test_tenant.id,
            user_id=test_user.id,
        )

        # 再尝试分享
        with pytest.raises(NotFoundException):
            await service.share_note(
                note_id=note["id"],
                tenant_id=test_tenant.id,
                user_id=test_user.id,
            )
