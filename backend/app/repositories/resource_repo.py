"""
智慧学伴 资源 Repository
继承 BaseRepository，扩展资源特有的数据库查询
"""
from typing import Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.resource import Resource, ResourceFavorite
from app.repositories.base import BaseRepository
from app.schemas.common import PaginationParams


class ResourceRepository(BaseRepository[Resource]):
    """资源 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(Resource, session)

    async def list_active_resources(
        self,
        pagination: PaginationParams,
        resource_type: Optional[str] = None,
        uploader_id: Optional[int] = None,
        search: Optional[str] = None,
        tenant_id: Optional[int] = None,
    ) -> Tuple[List[Resource], int]:
        """
        获取活跃资源列表（未软删除）

        Args:
            pagination: 分页参数
            resource_type: 资源类型筛选
            uploader_id: 上传者ID筛选
            search: 搜索关键词
            tenant_id: 租户ID

        Returns:
            (资源列表, 总数)
        """
        query = select(Resource).where(Resource.is_active == True, Resource.deleted_at.is_(None))

        if tenant_id:
            query = query.where(Resource.tenant_id == tenant_id)
        if resource_type:
            query = query.where(Resource.resource_type == resource_type)
        if uploader_id:
            query = query.where(Resource.uploader_id == uploader_id)
        if search:
            # 使用参数绑定防止 SQL 注入
            escaped = search.replace('%', '\\%').replace('_', '\\_')
            query = query.where(Resource.title.ilike(f"%{escaped}%"))

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = query.order_by(Resource.created_at.desc())
        query = query.offset(pagination.offset).limit(pagination.page_size)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_file_key(self, file_key: str) -> Optional[Resource]:
        """根据存储Key获取资源"""
        result = await self.session.execute(
            select(Resource).where(Resource.file_key == file_key, Resource.deleted_at.is_(None))
        )
        return result.scalars().first()

    async def soft_delete(self, resource_id: int) -> Optional[Resource]:
        """软删除资源（委托基类实现）"""
        return await super().soft_delete(resource_id)

    async def toggle_favorite(self, user_id: int, resource_id: int) -> bool:
        """切换收藏状态"""
        result = await self.session.execute(
            select(ResourceFavorite).where(
                ResourceFavorite.user_id == user_id,
                ResourceFavorite.resource_id == resource_id,
            )
        )
        existing = result.scalars().first()

        if existing:
            await self.session.delete(existing)
            await self.session.flush()
            return False  # 取消收藏
        else:
            favorite = ResourceFavorite(user_id=user_id, resource_id=resource_id)
            self.session.add(favorite)
            await self.session.flush()
            return True  # 添加收藏
