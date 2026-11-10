"""add learning_records table

Revision ID: c7d8e9f0a1b2
Revises: b2c3d4e5f6a7
Create Date: 2026-11-10 22:10:00.000000

任务2 学情分析 — 原始学情记录表，保留缺失/异常/重复等原始态问题，
由服务层做质量检查与清洗，便于在成果中说明处理方法。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c7d8e9f0a1b2"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 learning_records 表"""
    op.create_table(
        "learning_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("knowledge_point", sa.String(length=120), nullable=True, comment="知识点（可能缺失）"),
        sa.Column("record_type", sa.String(length=30), nullable=False, server_default="quiz", comment="记录类型"),
        sa.Column("source_ref", sa.String(length=120), nullable=True, comment="来源标识，用于溯源"),
        sa.Column("question_count", sa.Integer(), nullable=True, comment="题目数"),
        sa.Column("is_correct", sa.Boolean(), nullable=True, comment="单题对错"),
        sa.Column("score", sa.Float(), nullable=True, comment="得分（可能缺失）"),
        sa.Column("max_score", sa.Float(), nullable=True, comment="满分"),
        sa.Column("duration_seconds", sa.Integer(), nullable=True, comment="作答耗时（秒）"),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, comment="记录发生时间"),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.text("true"), comment="是否模拟数据"),
        sa.Column("raw_payload", sa.Text(), nullable=True, comment="原始记录 JSON"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_records_tenant_id", "learning_records", ["tenant_id"])
    op.create_index("ix_learning_records_student_id", "learning_records", ["student_id"])
    op.create_index("ix_learning_records_course_id", "learning_records", ["course_id"])
    op.create_index("ix_learning_records_knowledge_point", "learning_records", ["knowledge_point"])
    op.create_index("ix_learning_records_recorded_at", "learning_records", ["recorded_at"])
    op.create_index(
        "ix_learning_records_student_course", "learning_records", ["student_id", "course_id"]
    )
    op.create_index(
        "ix_learning_records_course_kp", "learning_records", ["course_id", "knowledge_point"]
    )


def downgrade() -> None:
    """删除 learning_records 表"""
    op.drop_index("ix_learning_records_course_kp", table_name="learning_records")
    op.drop_index("ix_learning_records_student_course", table_name="learning_records")
    op.drop_index("ix_learning_records_recorded_at", table_name="learning_records")
    op.drop_index("ix_learning_records_knowledge_point", table_name="learning_records")
    op.drop_index("ix_learning_records_course_id", table_name="learning_records")
    op.drop_index("ix_learning_records_student_id", table_name="learning_records")
    op.drop_index("ix_learning_records_tenant_id", table_name="learning_records")
    op.drop_table("learning_records")
