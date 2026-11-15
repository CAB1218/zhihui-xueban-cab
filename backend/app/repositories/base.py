"""
智慧学伴 基础 Repository
提供通用 CRUD 操作，所有具体 Repository 继承此类
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import Base
from app.schemas.common import PaginationParams

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    基础 Repository 类

    提供通用的数据库 CRUD 操作，子类可继承并扩展。
    使用泛型 ModelType 以支持任意 ORM 模型。

    Usage:
        class UserRepository(BaseRepository[User]):
            pass
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """
        初始化 Repository

        Args:
            model: ORM 模型类
            session: 异步数据库会话
        """
        self.model = model
        self.session = session

    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        根据ID获取记录

        Args:
            id: 记录ID

        Returns:
            Optional[ModelType]: 记录对象，不存在返回 None
        """
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalars().first()

    async def get_list(
        self,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
    ) -> tuple[List[ModelType], int]:
        """
        获取分页列表

        Args:
            pagination: 分页参数
            filters: 过滤条件字典

        Returns:
            tuple: (记录列表, 总数)
        """
        query = select(self.model)

        # 应用过滤条件
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        # 获取总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # 分页查询
        query = query.offset(pagination.offset).limit(pagination.page_size)
        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def create(self, obj_in: Dict[str, Any]) -> ModelType:
        """
        创建记录

        Args:
            obj_in: 创建数据字典

        Returns:
            ModelType: 创建的记录
        """
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(self, id: int, obj_in: Dict[str, Any]) -> Optional[ModelType]:
        """
        更新记录

        Args:
            id: 记录ID
            obj_in: 更新数据字典

        Returns:
            Optional[ModelType]: 更新后的记录
        """
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return None

        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: int) -> bool:
        """
        删除记录（硬删除）

        Args:
            id: 记录ID

        Returns:
            bool: 是否删除成功
        """
        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return False

        await self.session.delete(db_obj)
        await self.session.flush()
        return True

    async def soft_delete(self, id: int) -> Optional[ModelType]:
        """
        软删除记录

        Args:
            id: 记录ID

        Returns:
            Optional[ModelType]: 软删除后的记录
        """
        from datetime import datetime

        db_obj = await self.get_by_id(id)
        if db_obj is None:
            return None

        if hasattr(db_obj, "deleted_at"):
            db_obj.deleted_at = datetime.utcnow()
            await self.session.flush()
            await self.session.refresh(db_obj)

        return db_obj

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计记录数

        Args:
            filters: 过滤条件

        Returns:
            int: 记录数
        """
        query = select(func.count()).select_from(self.model)

        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        result = await self.session.execute(query)
        return result.scalar() or 0
