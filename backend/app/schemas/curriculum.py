"""
AI4EDU 课程梳理 Pydantic 数据契约
对应任务1：学习内容与要求清单 / 必要联系 / 材料出处
"""
from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 请求
# ---------------------------------------------------------------------------

class OutlineGenerateRequest(BaseModel):
    """课程梳理生成请求 — 用户开局输入想学的课程"""

    course_query: str = Field(..., min_length=1, max_length=200, description="想学的课程，如：初中数学七年级上册 / 数据结构(绪论与线性表)")
    subject: Optional[str] = Field(None, max_length=30, description="学科ID（math/physics/chemistry/chinese/english/cs...），不填由系统识别")
    grade_level: Optional[str] = Field(None, max_length=50, description="学段年级，如：七年级 / 高一 / 大二")
    scope_hint: Optional[str] = Field(None, max_length=500, description="范围限定说明，如：仅人教版2024新版第1-3章")
    use_web_search: bool = Field(True, description="是否联网检索课程材料")
    fallback_sample: bool = Field(False, description="LLM 不可用时是否回退到内置示例大纲")


# ---------------------------------------------------------------------------
# 大纲结构（与存储在 outline 字段中的 JSON 一致）
# ---------------------------------------------------------------------------

class LearningContent(BaseModel):
    """单条学习内容与对应要求"""

    topic: str = Field(..., description="学习内容主题")
    description: str = Field("", description="内容说明")
    requirement: str = Field("", description="课标对应要求表述（结果性/过程性行为动词句子）")
    requirement_level: str = Field("了解", description="要求水平：了解/理解/掌握/运用/经历/体验/感悟等")
    cognitive_level: str = Field("understand", description="认知水平 key：remember/understand/apply/analyze/evaluate/create")
    suggested_hours: Optional[float] = Field(None, description="建议课时数")


class Unit(BaseModel):
    """学习单元（章/模块）"""

    name: str = Field(..., description="单元名称")
    description: str = Field("", description="单元简介与在课程中的定位")
    contents: List[LearningContent] = Field(default_factory=list, description="本单元学习内容与要求清单")
    textbook_ref: str = Field("", description="教材章节出处，如：人教版七上 第2章")


class KnowledgeLink(BaseModel):
    """必要联系 — 供知识图谱与学情分析使用"""

    from_topic: str = Field(..., description="起始内容主题")
    to_topic: str = Field(..., description="指向内容主题")
    link_type: str = Field("prerequisite", description="prerequisite(前置)/related(相关)/cross_subject(跨学科)")
    description: str = Field("", description="联系说明：为什么先学它/怎么迁移")


class MaterialSource(BaseModel):
    """材料出处 — 范围清楚、可溯源"""

    title: str = Field(..., description="材料名称，如：义务教育数学课程标准（2022年版）")
    url: str = Field("", description="可访问链接（官网/在线资源）")
    source_type: str = Field("web", description="curriculum_standard/textbook/exam_outline/web")
    publisher: str = Field("", description="发布方/出版社")
    usage: str = Field("", description="本大纲中如何使用了该材料")


class CurriculumOutlineData(BaseModel):
    """完整大纲（JSON 导出格式与此结构一致）"""

    course: str = Field(..., description="课程名称")
    subject: str = Field("math", description="学科ID")
    subject_name: str = Field("数学", description="学科中文名")
    grade_level: str = Field("", description="学段/年级")
    scope: str = Field("", description="梳理范围说明（清楚界定边界）")
    scope_included: List[str] = Field(default_factory=list, description="本次梳理明确覆盖的范围（单元/章节/主题）")
    scope_excluded: List[str] = Field(default_factory=list, description="本次梳理明确排除或仅作了解的内容，避免越界")
    units: List[Unit] = Field(default_factory=list)
    connections: List[KnowledgeLink] = Field(default_factory=list)
    sources: List[MaterialSource] = Field(default_factory=list)
    generated_at: str = Field("", description="生成时间 ISO8601")
    model: str = Field("", description="生成模型")
    used_web_search: bool = Field(False, description="是否使用了联网检索材料")
    is_sample: bool = Field(False, description="是否为内置示例（LLM 不可用时的回退）")


# ---------------------------------------------------------------------------
# 响应
# ---------------------------------------------------------------------------

class CurriculumOutlineResponse(BaseModel):
    """课程梳理记录"""

    id: int
    course_query: str
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    scope_hint: Optional[str] = None
    title: Optional[str] = None
    outline: Optional[CurriculumOutlineData] = None
    model_name: Optional[str] = None
    used_web_search: Optional[bool] = None
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


ExportFormat = Literal["json", "md", "docx"]
