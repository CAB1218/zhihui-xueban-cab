"""add curriculum_outlines table

Revision ID: f6b7c8d9e401
Revises: e5a6b7c8d903
Create Date: 2026-11-09 20:00:00.000000

任务1 课程梳理 — 用户输入课程后联网检索+LLM 梳理的大纲存储表
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f6b7c8d9e401"
down_revision = "e5a6b7c8d903"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 curriculum_outlines 表"""
    op.create_table(
        "curriculum_outlines",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("course_query", sa.String(length=200), nullable=False, comment="用户输入的课程"),
        sa.Column("subject", sa.String(length=30), nullable=True, comment="学科ID"),
        sa.Column("grade_level", sa.String(length=50), nullable=True, comment="学段/年级"),
        sa.Column("scope_hint", sa.String(length=500), nullable=True, comment="范围限定说明"),
        sa.Column("title", sa.String(length=200), nullable=True, comment="大纲标题"),
        sa.Column("outline", sa.Text(), nullable=True, comment="完整大纲 JSON"),
        sa.Column("sources_json", sa.Text(), nullable=True, comment="联网检索原始材料 JSON"),
        sa.Column("model_name", sa.String(length=50), nullable=True, comment="生成模型"),
        sa.Column("used_web_search", sa.Boolean(), nullable=True, comment="是否使用了联网检索"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending", comment="pending/completed/failed"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_curriculum_outlines_tenant_id", "curriculum_outlines", ["tenant_id"])
    op.create_index("ix_curriculum_outlines_user_id", "curriculum_outlines", ["user_id"])
    op.create_index("ix_curriculum_outlines_status", "curriculum_outlines", ["status"])


def downgrade() -> None:
    """删除 curriculum_outlines 表"""
    op.drop_index("ix_curriculum_outlines_status", table_name="curriculum_outlines")
    op.drop_index("ix_curriculum_outlines_user_id", table_name="curriculum_outlines")
    op.drop_index("ix_curriculum_outlines_tenant_id", table_name="curriculum_outlines")
    op.drop_table("curriculum_outlines")
