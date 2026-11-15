"""
智慧学伴 租户创建脚本
用于创建新租户及其数据库Schema
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.database import Base, async_session_factory, engine
from app.models.tenant import Tenant


async def create_tenant(
    name: str,
    slug: str,
    plan: str = "free",
    max_users: int = 50,
    max_storage_mb: int = 1024,
    domain: str = None,
):
    """
    创建新租户

    Args:
        name: 租户名称
        slug: 租户标识（URL友好）
        plan: 套餐类型
        max_users: 最大用户数
        max_storage_mb: 最大存储空间(MB)
        domain: 绑定域名
    """
    from sqlalchemy.future import select

    async with async_session_factory() as session:
        # 检查 slug 是否已存在
        result = await session.execute(select(Tenant).where(Tenant.slug == slug))
        existing = result.scalars().first()

        if existing:
            print(f"租户标识 '{slug}' 已存在，ID: {existing.id}")
            return

        # 创建租户记录
        # 先查询最大ID以确定Schema名
        result = await session.execute(select(Tenant).order_by(Tenant.id.desc()).limit(1))
        last_tenant = result.scalars().first()
        next_id = (last_tenant.id + 1) if last_tenant else 1

        schema_name = f"tenant_{next_id}"

        tenant = Tenant(
            name=name,
            slug=slug,
            schema_name=schema_name,
            domain=domain,
            plan=plan,
            max_users=max_users,
            max_storage_mb=max_storage_mb,
            settings="{}",
            is_active=True,
        )
        session.add(tenant)
        await session.flush()

        # 创建租户Schema
        tenant_id = tenant.id
        actual_schema = f"tenant_{tenant_id}"

        # 如果ID与预期不同，更新schema_name
        if actual_schema != schema_name:
            tenant.schema_name = actual_schema

        # 创建数据库Schema
        await session.execute(f"CREATE SCHEMA IF NOT EXISTS {actual_schema}")
        # 在新Schema中创建所有表
        # TODO: 使用 Alembic 或手动SQL在租户Schema中创建表

        await session.commit()

        print(f"租户 '{name}' 创建成功！")
        print(f"  ID: {tenant_id}")
        print(f"  Slug: {slug}")
        print(f"  Schema: {actual_schema}")
        print(f"  套餐: {plan}")


async def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="创建智慧学伴租户")
    parser.add_argument("--name", required=True, help="租户名称")
    parser.add_argument("--slug", required=True, help="租户标识(URL友好)")
    parser.add_argument("--plan", default="free", choices=["free", "basic", "premium", "enterprise"], help="套餐类型")
    parser.add_argument("--max-users", type=int, default=50, help="最大用户数")
    parser.add_argument("--domain", default=None, help="绑定域名")

    args = parser.parse_args()

    await create_tenant(
        name=args.name,
        slug=args.slug,
        plan=args.plan,
        max_users=args.max_users,
        domain=args.domain,
    )


if __name__ == "__main__":
    asyncio.run(main())
