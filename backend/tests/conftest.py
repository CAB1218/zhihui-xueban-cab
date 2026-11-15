"""
智慧学伴 测试配置
pytest fixtures: async_client, db_session, test_user, auth_headers, test_tenant
使用 SQLite 内存数据库，模拟 Redis/Neo4j
"""
import asyncio
from typing import AsyncGenerator, Dict, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.security import create_access_token, hash_password
from app.database import Base
# 导入所有模型以确保 Base.metadata 包含所有表（测试数据库创建需要）
from app.models import (  # noqa: F401
    tenant, user, course, resource, note, scene, notification,
    agent, classroom, diagnosis, buddy, audit, lesson_plan,
    flash_card, help, permission,
)
from app.models.note import Note, NoteVersion
from app.models.tenant import Tenant
from app.models.user import User


# ============ 测试数据库引擎 ============

# 使用 SQLite 内存数据库进行测试
TEST_DATABASE_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    # SQLite 不支持 schema，将所有 schema 映射到 None
    execution_options={"schema_translate_map": {None: None, "public": None, "clickhouse": None}},
)

test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ============ 事件循环 ============

@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    创建会话级别的事件循环

    Returns:
        事件循环实例
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============ 数据库 Fixtures ============

def _create_test_tables(sync_conn):
    """同步回调：创建测试表，移除 PostgreSQL schema 以兼容 SQLite"""
    # 临时移除所有表的 schema（SQLite 不支持 schema）
    original_schemas = {}
    for table in Base.metadata.tables.values():
        original_schemas[table.name] = table.schema
        table.schema = None
    
    try:
        Base.metadata.create_all(sync_conn)
    finally:
        # 恢复原始 schema
        for table in Base.metadata.tables.values():
            table.schema = original_schemas.get(table.name)


def _drop_test_tables(sync_conn):
    """同步回调：删除测试表，移除 PostgreSQL schema 以兼容 SQLite"""
    original_schemas = {}
    for table in Base.metadata.tables.values():
        original_schemas[table.name] = table.schema
        table.schema = None
    
    try:
        Base.metadata.drop_all(sync_conn)
    finally:
        for table in Base.metadata.tables.values():
            table.schema = original_schemas.get(table.name)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    创建测试数据库会话

    每个测试函数使用独立的数据库，测试结束后清理

    Yields:
        AsyncSession: 测试数据库会话
    """
    # 创建所有表（移除 schema 以兼容 SQLite）
    async with test_engine.begin() as conn:
        await conn.run_sync(_create_test_tables)

    async with test_session_factory() as session:
        yield session
        await session.rollback()

    # 清理所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(_drop_test_tables)


# ============ 测试租户 Fixture ============

@pytest_asyncio.fixture(scope="function")
async def test_tenant(db_session: AsyncSession) -> Tenant:
    """
    创建测试租户

    Args:
        db_session: 数据库会话

    Returns:
        Tenant: 测试租户实例
    """
    tenant = Tenant(
        name="测试学校",
        slug="test-school",
        schema_name="tenant_test",
        plan="premium",
        max_users=100,
        is_active=True,
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


# ============ 测试用户 Fixture ============

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """
    创建测试用户

    Args:
        db_session: 数据库会话
        test_tenant: 测试租户

    Returns:
        User: 测试用户实例
    """
    user = User(
        tenant_id=test_tenant.id,
        email="test@ai4edu.com",
        password_hash=hash_password("Test123456"),
        nickname="测试用户",
        role="student",
        default_scene="classroom",
        locale="zh-CN",
        timezone="Asia/Shanghai",
        onboarding_completed=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_teacher(db_session: AsyncSession, test_tenant: Tenant) -> User:
    """
    创建测试教师用户

    Args:
        db_session: 数据库会话
        test_tenant: 测试租户

    Returns:
        User: 测试教师实例
    """
    teacher = User(
        tenant_id=test_tenant.id,
        email="teacher@ai4edu.com",
        password_hash=hash_password("Teacher123456"),
        nickname="测试教师",
        role="teacher",
        default_scene="classroom",
        locale="zh-CN",
        timezone="Asia/Shanghai",
        onboarding_completed=True,
        is_active=True,
    )
    db_session.add(teacher)
    await db_session.commit()
    await db_session.refresh(teacher)
    return teacher


# ============ 认证 Fixtures ============

@pytest_asyncio.fixture(scope="function")
async def auth_headers(test_user: User) -> Dict[str, str]:
    """
    生成认证请求头

    Args:
        test_user: 测试用户

    Returns:
        Dict[str, str]: 包含 Bearer Token 的请求头
    """
    access_token = create_access_token(
        data={"sub": test_user.id, "role": test_user.role}
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture(scope="function")
async def teacher_auth_headers(test_teacher: User) -> Dict[str, str]:
    """
    生成教师认证请求头

    Args:
        test_teacher: 测试教师

    Returns:
        Dict[str, str]: 包含 Bearer Token 的请求头
    """
    access_token = create_access_token(
        data={"sub": test_teacher.id, "role": test_teacher.role}
    )
    return {"Authorization": f"Bearer {access_token}"}


# ============ HTTP 客户端 Fixture ============

@pytest_asyncio.fixture(scope="function")
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    创建异步HTTP测试客户端

    注入测试数据库会话，覆盖应用默认数据库依赖

    Yields:
        AsyncClient: 异步HTTP客户端
    """
    from app.main import app
    from app.dependencies import get_db

    async def override_get_db():
        yield db_session

    # 覆盖数据库依赖
    app.dependency_overrides[get_db] = override_get_db

    # 在测试环境中禁用限流中间件，避免429干扰认证测试
    from app.middleware.rate_limit import RateLimitMiddleware
    original_middlewares = app.user_middleware.copy()
    app.user_middleware = [m for m in app.user_middleware if m.cls != RateLimitMiddleware]

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client

    # 清理依赖覆盖和中间件
    app.dependency_overrides.clear()
    app.user_middleware = original_middlewares


# ============ 模拟 Redis ============

class MockRedis:
    """
    模拟 Redis 客户端
    使用内存字典存储数据，支持基本的 get/set/delete 操作
    """

    def __init__(self) -> None:
        self._data: Dict[str, str] = {}
        self._expiry: Dict[str, float] = {}

    async def get(self, key: str) -> str | None:
        """获取键值"""
        return self._data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        """设置键值"""
        self._data[key] = value
        return True

    async def delete(self, key: str) -> int:
        """删除键"""
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return key in self._data

    async def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        return True

    async def incr(self, key: str) -> int:
        """递增"""
        val = int(self._data.get(key, "0")) + 1
        self._data[key] = str(val)
        return val

    async def pipeline(self):
        """返回自身模拟管道"""
        return self

    async def execute(self):
        """执行管道命令"""
        return []


@pytest.fixture(scope="function")
def mock_redis() -> MockRedis:
    """
    提供模拟 Redis 客户端

    Returns:
        MockRedis: 模拟Redis实例
    """
    return MockRedis()


# ============ 模拟 Neo4j ============

class MockNeo4jDriver:
    """
    模拟 Neo4j 驱动
    提供基本的会话模拟
    """

    def __init__(self) -> None:
        self._nodes: list = []

    def session(self, **kwargs):
        """创建模拟会话"""
        return MockNeo4jSession(self._nodes)

    async def close(self):
        """关闭驱动"""
        pass


class MockNeo4jSession:
    """模拟 Neo4j 会话"""

    def __init__(self, nodes: list) -> None:
        self._nodes = nodes

    def run(self, query: str, **kwargs):
        """执行查询"""
        return MockNeo4jResult(self._nodes)

    async def close(self):
        """关闭会话"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockNeo4jResult:
    """模拟 Neo4j 查询结果"""

    def __init__(self, nodes: list) -> None:
        self._nodes = nodes

    def data(self):
        """返回查询数据"""
        return self._nodes

    def single(self):
        """返回单条结果"""
        return self._nodes[0] if self._nodes else None


@pytest.fixture(scope="function")
def mock_neo4j() -> MockNeo4jDriver:
    """
    提供模拟 Neo4j 驱动

    Returns:
        MockNeo4jDriver: 模拟Neo4j驱动实例
    """
    return MockNeo4jDriver()


# ============ 测试笔记 Fixture ============

@pytest_asyncio.fixture(scope="function")
async def test_note(db_session: AsyncSession, test_tenant: Tenant, test_user: User) -> Note:
    """
    创建测试笔记

    Args:
        db_session: 数据库会话
        test_tenant: 测试租户
        test_user: 测试用户

    Returns:
        Note: 测试笔记实例
    """
    note = Note(
        tenant_id=test_tenant.id,
        title="测试笔记",
        content="这是一条测试笔记的内容",
        content_plain="这是一条测试笔记的内容",
        note_type="personal",
        owner_id=test_user.id,
        tags='["测试"]',
        word_count=10,
        version=1,
        is_deleted=False,
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)
    return note
