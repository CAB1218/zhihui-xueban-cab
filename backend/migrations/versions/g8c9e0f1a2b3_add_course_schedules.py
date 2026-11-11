"""add course_schedules table

Revision ID: g8c9e0f1a2b3
Revises: c7d8e9f0a1b2
Create Date: 2026-11-11 17:30:00.000000

场景仪表盘「导入课表」功能 — 用户个人课表，按 星期 + 起止时间 存储，
支持整学期循环课表；导入来源文件名留痕，便于回溯。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "g8c9e0f1a2b3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建 course_schedules 表"""
    op.create_table(
        "course_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False, comment="租户ID"),
        sa.Column("user_id", sa.Integer(), nullable=False, comment="课表所属用户ID"),
        sa.Column("course_name", sa.String(length=120), nullable=False, comment="课程名称"),
        sa.Column("teacher", sa.String(length=60), nullable=True, comment="任课教师"),
        sa.Column("location", sa.String(length=120), nullable=True, comment="上课地点"),
        sa.Column("weekday", sa.Integer(), nullable=False, comment="星期（1=周一 … 7=周日）"),
        sa.Column("start_time", sa.String(length=5), nullable=False, comment="开始时间 HH:mm"),
        sa.Column("end_time", sa.String(length=5), nullable=False, comment="结束时间 HH:mm"),
        sa.Column("weeks", sa.String(length=60), nullable=True, comment="上课周次"),
        sa.Column("note", sa.Text(), nullable=True, comment="备注"),
        sa.Column("source_file", sa.String(length=200), nullable=True, comment="导入来源文件名"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_course_schedules_tenant_id", "course_schedules", ["tenant_id"])
    op.create_index("ix_course_schedules_user_id", "course_schedules", ["user_id"])
    op.create_index(
        "ix_course_schedules_user_weekday", "course_schedules", ["user_id", "weekday"]
    )


def downgrade() -> None:
    """删除 course_schedules 表"""
    op.drop_index("ix_course_schedules_user_weekday", table_name="course_schedules")
    op.drop_index("ix_course_schedules_user_id", table_name="course_schedules")
    op.drop_index("ix_course_schedules_tenant_id", table_name="course_schedules")
    op.drop_table("course_schedules")
