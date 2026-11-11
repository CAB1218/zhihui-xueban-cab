"""add llm_provider_configs table

Revision ID: h9d0e1f2b3c4
Revises: g8c9e0f1a2b3
Create Date: 2026-11-11 20:50:00.000000

「AI 对话 → 模型配置」功能 — 管理员可在页面上填写 DeepSeek / 通义千问 / 混元的
API Key、API Base 与模型名，保存后立即生效，无需改 .env 重启后端。
API Key 以 AES 加密存储，接口只回显掩码。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "h9d0e1f2b3c4"
down_revision = "g8c9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 llm_provider_configs 表"""
    op.create_table(
        "llm_provider_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, comment="服务商"),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True, comment="API Key（AES 加密）"),
        sa.Column("api_base", sa.String(length=200), nullable=True, comment="API Base"),
        sa.Column("model_name", sa.String(length=100), nullable=True, comment="模型名"),
        sa.Column("last_test_ok", sa.Boolean(), nullable=True, comment="最近一次测试是否通过"),
        sa.Column("last_test_message", sa.Text(), nullable=True, comment="最近一次测试结果说明"),
        sa.Column("last_test_at", sa.DateTime(), nullable=True, comment="最近一次测试时间"),
        sa.Column("updated_by", sa.Integer(), nullable=True, comment="最后修改人"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider"),
    )
    op.create_index("ix_llm_provider_configs_provider", "llm_provider_configs", ["provider"])


def downgrade() -> None:
    """删除 llm_provider_configs 表"""
    op.drop_index("ix_llm_provider_configs_provider", table_name="llm_provider_configs")
    op.drop_table("llm_provider_configs")
