"""任务3：个性化学习建议方案表

Revision ID: i0e1f2a3c4d5
Revises: h9d0e1f2b3c4
Create Date: 2026-11-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i0e1f2a3c4d5"
down_revision: Union[str, None] = "h9d0e1f2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False, comment="方案ID"),
        sa.Column("tenant_id", sa.Integer(), nullable=False, comment="租户ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="发起生成的用户ID"),
        sa.Column("student_id", sa.Integer(), nullable=False, comment="方案面向的学生ID"),
        sa.Column("student_name", sa.String(length=50), nullable=True, comment="学生姓名快照"),
        sa.Column("course_id", sa.Integer(), nullable=True, comment="课程ID"),
        sa.Column("course_name", sa.String(length=200), nullable=True, comment="课程名称快照"),
        sa.Column("title", sa.String(length=200), nullable=True, comment="方案标题"),
        sa.Column("duration_days", sa.Integer(), nullable=False, server_default="7", comment="建议周期（天）"),
        sa.Column("focus", sa.String(length=200), nullable=True, comment="教师指定优先补强的知识点"),
        sa.Column("plan_json", sa.Text(), nullable=True, comment="完整方案 JSON"),
        sa.Column("source_json", sa.Text(), nullable=True, comment="生成依据快照"),
        sa.Column("model_name", sa.String(length=50), nullable=True, comment="生成引擎"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="completed", comment="completed/failed"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()"), comment="更新时间"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_plans_tenant_id", "learning_plans", ["tenant_id"])
    op.create_index("ix_learning_plans_user_id", "learning_plans", ["user_id"])
    op.create_index("ix_learning_plans_student_id", "learning_plans", ["student_id"])
    op.create_index("ix_learning_plans_course_id", "learning_plans", ["course_id"])
    op.create_index("ix_learning_plans_status", "learning_plans", ["status"])


def downgrade() -> None:
    op.drop_index("ix_learning_plans_status", table_name="learning_plans")
    op.drop_index("ix_learning_plans_course_id", table_name="learning_plans")
    op.drop_index("ix_learning_plans_student_id", table_name="learning_plans")
    op.drop_index("ix_learning_plans_user_id", table_name="learning_plans")
    op.drop_index("ix_learning_plans_tenant_id", table_name="learning_plans")
    op.drop_table("learning_plans")
