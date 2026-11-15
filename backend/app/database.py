"""
智慧学伴 数据库连接管理
支持 PostgreSQL 多租户 Schema 隔离
"""
import re
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import text

from app.config import settings

# 异步数据库引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# 异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话的依赖注入函数
    用于普通请求（公共Schema）
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_tenant_db(tenant_schema: str) -> AsyncGenerator[AsyncSession, None]:
    """
    获取租户专属数据库会话
    动态设置 search_path 到租户 Schema，实现多租户数据隔离

    Args:
        tenant_schema: 租户Schema名称，如 tenant_1
    """
    async with async_session_factory() as session:
        try:
            # 设置租户Schema搜索路径
            # tenant_schema 由 get_tenant_schema() 生成，格式为 tenant_{int} 或 public
            # 验证格式防止SQL注入
            if tenant_schema != "public" and not re.match(r"^tenant_\d+$", tenant_schema):
                raise ValueError(f"Invalid tenant schema name: {tenant_schema}")
            await session.execute(
                text(f"SET search_path TO {tenant_schema}, public")
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tenant_schema(tenant_id: int) -> None:
    """
    为新租户创建独立的数据库Schema

    Args:
        tenant_id: 租户ID
    """
    schema_name = f"tenant_{tenant_id}"
    # tenant_id 为 int 类型，schema_name 格式安全
    async with async_session_factory() as session:
        await session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        # 在租户Schema中创建所有表
        # 依次执行各表的CREATE TABLE语句
        await session.commit()
