"""
赛题数据集 ORM 模型（七年级数学 · 模拟学情数据）

对应赛题资料「4_赛题数据/模拟学情数据」的三张支撑表：
- contest_course_requirements  课程要求（T01—T03 主题与 9 条观察指标）
- contest_exam_nodes           测验节点（N01 上学期期末 / N02 下学期期末）
- contest_materials            题目与材料（Q001—Q054 题目、L01—L03 学习卡、B01—B08 教材切片）

作答记录不落本模块，而是进入 learning_records（analysis 服务的输入），
raw_payload 中保留赛题原始字段（材料编号/作答事件编号/评分点得分等）以便溯源。
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContestCourseRequirement(Base):
    """课程要求：主题 → 观察指标 → 课标/教材出处"""

    __tablename__ = "contest_course_requirements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True
    )
    topic_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True, comment="主题编号 T01—T03")
    topic: Mapped[str] = mapped_column(String(100), nullable=False, comment="主题名称")
    topic_goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="主题目标")
    indicator_code: Mapped[str] = mapped_column(String(20), nullable=False, comment="指标编号 如 T01I1")
    indicator: Mapped[str] = mapped_column(String(200), nullable=False, comment="观察指标内容")
    cr_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, comment="课标整理编号 CR01—CR03")
    cr_pages: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="课标文件页／正文页")
    textbook_pages: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="教材正文页范围")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ContestExamNode(Base):
    """测验节点"""

    __tablename__ = "contest_exam_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True
    )
    node_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True, comment="节点编号 N01/N02")
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="模拟测验日期")
    taught_topics: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="已教及测量主题")
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="教学进度说明")
    question_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="可用题目编号（、分隔）")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class ContestMaterial(Base):
    """题目与材料：题目 Q001—Q054、学习卡 L01—L03、教材切片 B01—B08"""

    __tablename__ = "contest_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tenants.id"), nullable=False, index=True
    )
    material_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True, comment="材料编号")
    topic_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, index=True, comment="主题编号")
    material_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="题目/学习卡/教材")
    question_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="选择题/填空题/解答题")
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="题干或内容")
    options: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="选择题选项")
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="参考答案")
    analysis: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="参考解析")
    max_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="满分")
    grading_points: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="评分点")
    indicator_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="观察指标编号")
    source_file: Mapped[Optional[str]] = mapped_column(String(300), nullable=True, comment="来源或资料文件")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
