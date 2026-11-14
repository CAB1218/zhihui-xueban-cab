"""赛题数据集支撑表（课程要求/测验节点/题目与材料）

Revision ID: j1f2a3b4c5d6
Revises: i0e1f2a3c4d5
Create Date: 2026-11-14
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j1f2a3b4c5d6"
down_revision: Union[str, None] = "i0e1f2a3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contest_course_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("topic_code", sa.String(length=10), nullable=False, comment="主题编号 T01—T03"),
        sa.Column("topic", sa.String(length=100), nullable=False, comment="主题名称"),
        sa.Column("topic_goal", sa.Text(), nullable=True, comment="主题目标"),
        sa.Column("indicator_code", sa.String(length=20), nullable=False, comment="指标编号"),
        sa.Column("indicator", sa.String(length=200), nullable=False, comment="观察指标"),
        sa.Column("cr_code", sa.String(length=10), nullable=True, comment="课标整理编号"),
        sa.Column("cr_pages", sa.String(length=50), nullable=True, comment="课标文件页／正文页"),
        sa.Column("textbook_pages", sa.String(length=100), nullable=True, comment="教材正文页"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contest_course_requirements_tenant_id", "contest_course_requirements", ["tenant_id"])
    op.create_index("ix_contest_course_requirements_topic_code", "contest_course_requirements", ["topic_code"])

    op.create_table(
        "contest_exam_nodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("node_code", sa.String(length=10), nullable=False, comment="节点编号 N01/N02"),
        sa.Column("exam_date", sa.Date(), nullable=True, comment="模拟测验日期"),
        sa.Column("taught_topics", sa.String(length=100), nullable=True, comment="已教及测量主题"),
        sa.Column("note", sa.Text(), nullable=True, comment="说明"),
        sa.Column("question_codes", sa.Text(), nullable=True, comment="可用题目编号"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contest_exam_nodes_tenant_id", "contest_exam_nodes", ["tenant_id"])
    op.create_index("ix_contest_exam_nodes_node_code", "contest_exam_nodes", ["node_code"])

    op.create_table(
        "contest_materials",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("material_code", sa.String(length=10), nullable=False, comment="材料编号"),
        sa.Column("topic_code", sa.String(length=10), nullable=True, comment="主题编号"),
        sa.Column("material_type", sa.String(length=20), nullable=False, comment="题目/学习卡/教材"),
        sa.Column("question_type", sa.String(length=20), nullable=True, comment="题型"),
        sa.Column("content", sa.Text(), nullable=True, comment="题干或内容"),
        sa.Column("options", sa.Text(), nullable=True, comment="选项"),
        sa.Column("answer", sa.Text(), nullable=True, comment="参考答案"),
        sa.Column("analysis", sa.Text(), nullable=True, comment="参考解析"),
        sa.Column("max_score", sa.Integer(), nullable=True, comment="满分"),
        sa.Column("grading_points", sa.Text(), nullable=True, comment="评分点"),
        sa.Column("indicator_code", sa.String(length=50), nullable=True, comment="指标编号"),
        sa.Column("source_file", sa.String(length=300), nullable=True, comment="来源或资料文件"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_contest_materials_tenant_id", "contest_materials", ["tenant_id"])
    op.create_index("ix_contest_materials_material_code", "contest_materials", ["material_code"])
    op.create_index("ix_contest_materials_topic_code", "contest_materials", ["topic_code"])


def downgrade() -> None:
    op.drop_index("ix_contest_materials_topic_code", table_name="contest_materials")
    op.drop_index("ix_contest_materials_material_code", table_name="contest_materials")
    op.drop_index("ix_contest_materials_tenant_id", table_name="contest_materials")
    op.drop_table("contest_materials")
    op.drop_index("ix_contest_exam_nodes_node_code", table_name="contest_exam_nodes")
    op.drop_index("ix_contest_exam_nodes_tenant_id", table_name="contest_exam_nodes")
    op.drop_table("contest_exam_nodes")
    op.drop_index("ix_contest_course_requirements_topic_code", table_name="contest_course_requirements")
    op.drop_index("ix_contest_course_requirements_tenant_id", table_name="contest_course_requirements")
    op.drop_table("contest_course_requirements")
