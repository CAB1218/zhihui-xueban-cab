"""
智慧学伴 Alembic 迁移环境配置
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base

# 导入所有模型以确保 Base.metadata 包含所有表
from app.models import tenant, user, course, resource, note, scene, notification
from app.models import agent, classroom, diagnosis, buddy, audit, lesson_plan
from app.models import flash_card, help, permission
from app.models import analytics  # AnalyticsEvent 标记为 clickhouse schema，不会被迁移到 PostgreSQL

# Alembic Config 对象
config = context.config

# 设置数据库URL
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL_SYNC)

# Python 日志配置
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData 对象，用于自动生成迁移
target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    过滤 Alembic autogenerate 的对象
    排除 clickhouse schema 的表（AnalyticsEvent 等 ClickHouse 专用表）
    """
    if type_ == "table" and object.schema == "clickhouse":
        return False
    return True


def run_migrations_offline() -> None:
    """
    离线模式运行迁移
    只生成 SQL 脚本，不连接数据库
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移
    连接数据库并执行迁移
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
