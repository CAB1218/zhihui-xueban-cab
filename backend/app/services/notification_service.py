"""
智慧学伴 通知服务
创建通知、已读标记、实时推送
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.notification import Notification, NotificationSetting
from app.schemas.common import PaginatedResponse, PaginationParams

logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        content: Optional[str] = None,
        link: Optional[str] = None,
        sender_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        metadata_json: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        创建通知

        Args:
            user_id: 接收用户ID
            notification_type: 通知类型 system/course/assignment/social/ai
            title: 通知标题
            content: 通知内容
            link: 关联链接
            sender_id: 发送者ID
            tenant_id: 租户ID
            metadata_json: 元数据

        Returns:
            创建的通知信息
        """
        notification = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            content=content,
            link=link,
            sender_id=sender_id,
            is_read=False,
            metadata_json=json.dumps(metadata_json, ensure_ascii=False) if metadata_json else None,
        )
        self.db.add(notification)
        await self.db.flush()

        # 尝试实时推送
        try:
            from app.websocket.notification_handler import notification_handler
            await notification_handler.push_notification(
                user_id=user_id,
                notification={
                    "id": notification.id,
                    "type": notification_type,
                    "title": title,
                    "content": content,
                    "link": link,
                },
            )
        except Exception as e:
            logger.warning(f"实时推送失败: {e}")

        return self._notification_to_dict(notification)

    async def list_notifications(
        self,
        user_id: int,
        pagination: PaginationParams,
        notification_type: Optional[str] = None,
        unread_only: bool = False,
    ) -> PaginatedResponse:
        """
        获取通知列表

        Args:
            user_id: 用户ID
            pagination: 分页参数
            notification_type: 通知类型筛选
            unread_only: 仅显示未读

        Returns:
            分页通知列表
        """
        conditions = [Notification.user_id == user_id]

        if notification_type:
            conditions.append(Notification.notification_type == notification_type)
        if unread_only:
            conditions.append(Notification.is_read == False)

        # 总数
        count_stmt = select(func.count(Notification.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # 未读数
        unread_count_stmt = select(func.count(Notification.id)).where(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        )
        unread_result = await self.db.execute(unread_count_stmt)
        unread_count = unread_result.scalar() or 0

        # 数据
        stmt = (
            select(Notification)
            .where(and_(*conditions))
            .order_by(desc(Notification.created_at))
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
        result = await self.db.execute(stmt)
        notifications = result.scalars().all()

        items = [self._notification_to_dict(n) for n in notifications]

        return PaginatedResponse(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
        )

    async def get_unread_count(self, user_id: int) -> int:
        """
        获取未读通知数量

        Args:
            user_id: 用户ID

        Returns:
            未读数量
        """
        stmt = select(func.count(Notification.id)).where(
            and_(Notification.user_id == user_id, Notification.is_read == False)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def mark_read(
        self,
        notification_id: int,
        user_id: int,
    ) -> bool:
        """
        标记通知为已读

        Args:
            notification_id: 通知ID
            user_id: 用户ID

        Returns:
            是否标记成功
        """
        stmt = select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        notification = result.scalars().first()

        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.utcnow()
        await self.db.flush()
        return True

    async def mark_all_read(self, user_id: int) -> int:
        """
        标记所有通知为已读

        Args:
            user_id: 用户ID

        Returns:
            标记的数量
        """
        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.is_read == False))
            .values(is_read=True, read_at=datetime.utcnow())
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def delete_notification(
        self,
        notification_id: int,
        user_id: int,
    ) -> bool:
        """
        删除通知

        Args:
            notification_id: 通知ID
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        stmt = select(Notification).where(
            and_(Notification.id == notification_id, Notification.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        notification = result.scalars().first()

        if not notification:
            return False

        await self.db.delete(notification)
        await self.db.flush()
        return True

    async def update_settings(
        self,
        user_id: int,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        更新通知设置

        Args:
            user_id: 用户ID
            **kwargs: 设置字段

        Returns:
            更新后的设置
        """
        stmt = select(NotificationSetting).where(NotificationSetting.user_id == user_id)
        result = await self.db.execute(stmt)
        settings = result.scalars().first()

        if not settings:
            settings = NotificationSetting(user_id=user_id)
            self.db.add(settings)

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        await self.db.flush()

        return self._settings_to_dict(settings)

    async def get_settings(self, user_id: int) -> Dict[str, Any]:
        """
        获取通知设置

        Args:
            user_id: 用户ID

        Returns:
            通知设置
        """
        stmt = select(NotificationSetting).where(NotificationSetting.user_id == user_id)
        result = await self.db.execute(stmt)
        settings = result.scalars().first()

        if not settings:
            return {
                "user_id": user_id,
                "system_enabled": True,
                "course_enabled": True,
                "assignment_enabled": True,
                "social_enabled": True,
                "ai_enabled": True,
                "email_enabled": False,
                "push_enabled": True,
            }

        return self._settings_to_dict(settings)

    def _notification_to_dict(self, notification: Notification) -> Dict[str, Any]:
        """将Notification模型转换为字典"""
        metadata = None
        if notification.metadata_json:
            try:
                metadata = json.loads(notification.metadata_json)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": notification.id,
            "user_id": notification.user_id,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "content": notification.content,
            "link": notification.link,
            "sender_id": notification.sender_id,
            "is_read": notification.is_read,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
            "metadata": metadata,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        }

    def _settings_to_dict(self, settings: NotificationSetting) -> Dict[str, Any]:
        """将NotificationSetting模型转换为字典"""
        return {
            "user_id": settings.user_id,
            "system_enabled": settings.system_enabled,
            "course_enabled": settings.course_enabled,
            "assignment_enabled": settings.assignment_enabled,
            "social_enabled": settings.social_enabled,
            "ai_enabled": settings.ai_enabled,
            "email_enabled": settings.email_enabled,
            "push_enabled": settings.push_enabled,
            "quiet_hours_start": settings.quiet_hours_start,
            "quiet_hours_end": settings.quiet_hours_end,
        }
