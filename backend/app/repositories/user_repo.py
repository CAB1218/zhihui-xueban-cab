"""
智慧学伴 用户 Repository
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        根据邮箱获取用户

        Args:
            email: 邮箱地址

        Returns:
            Optional[User]: 用户对象，不存在返回 None
        """
        result = await self.session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalars().first()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        """
        根据手机号获取用户

        Args:
            phone: 手机号

        Returns:
            Optional[User]: 用户对象，不存在返回 None
        """
        result = await self.session.execute(
            select(User).where(User.phone == phone, User.deleted_at.is_(None))
        )
        return result.scalars().first()

    async def get_by_tenant(self, tenant_id: int) -> list[User]:
        """
        获取租户下所有用户

        Args:
            tenant_id: 租户ID

        Returns:
            list[User]: 用户列表
        """
        result = await self.session.execute(
            select(User).where(User.tenant_id == tenant_id, User.deleted_at.is_(None))
        )
        return list(result.scalars().all())

    async def update_last_login(self, user_id: int, ip_address: str) -> None:
        """
        更新用户最后登录信息

        Args:
            user_id: 用户ID
            ip_address: 登录IP
        """
        from datetime import datetime

        user = await self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            user.last_login_ip = ip_address
            await self.session.flush()
