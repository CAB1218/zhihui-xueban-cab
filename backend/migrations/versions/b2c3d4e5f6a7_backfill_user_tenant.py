"""backfill user tenant_id to default tenant

自注册用户创建时未写 tenant_id，导致所有带 tenant_id 外键的业务表
（notes / classrooms / diagnoses / curriculum_outlines ...）插入失败。
本迁移把历史 NULL 用户归属到默认租户（id 最小的租户）。

Revision ID: b2c3d4e5f6a7
Revises: f6b7c8d9e401
Create Date: 2026-11-10 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f6b7c8d9e401"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) 历史用户：tenant_id 为 NULL 的统一归属到默认租户
    op.execute(
        """
        UPDATE users
           SET tenant_id = (SELECT MIN(id) FROM tenants)
         WHERE tenant_id IS NULL
           AND EXISTS (SELECT 1 FROM tenants)
        """
    )
    # 2) 兜底：若 tenants 表为空，则创建默认租户后再回填
    op.execute(
        """
        INSERT INTO tenants (name, slug, schema_name, plan, max_users, max_storage_mb, is_active, created_at, updated_at)
        SELECT '默认租户', 'default', 'public', 'free', 1000, 10240, true, NOW(), NOW()
         WHERE NOT EXISTS (SELECT 1 FROM tenants)
        """
    )
    op.execute("UPDATE users SET tenant_id = (SELECT MIN(id) FROM tenants) WHERE tenant_id IS NULL")


def downgrade() -> None:
    # 数据回填不可逆，无需回滚
    pass
