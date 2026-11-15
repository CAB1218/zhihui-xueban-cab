"""
智慧学伴 知识图谱模块 Pydantic Schema 集中定义
包含 Misconception、CrossSubject、Task、CognitiveGoal 等所有图谱相关 Schema
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Literal

from pydantic import BaseModel, Field


# ========== Misconception ==========

class MisconceptionItem(BaseModel):
    """误解标注项（读取/响应）"""

    mc_id: str
    misconception: str
    correction: str
    topic: str
    keywords: List[str] = Field(default_factory=list)
    source: Literal["teacher", "ai", "system"]
    annotated_by: Optional[int] = None
    annotated_at: datetime
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class MisconceptionCreate(BaseModel):
    """创建误解标注（请求体）"""

    misconception: str = Field(..., min_length=1, max_length=500)
    correction: str = Field(..., min_length=1, max_length=2000)
    topic: str = Field(..., min_length=1, max_length=200)
    keywords: List[str] = Field(default_factory=list, max_length=10)


class MisconceptionUpdate(BaseModel):
    """更新误解标注（请求体，所有字段可选）"""

    misconception: Optional[str] = Field(None, max_length=500)
    correction: Optional[str] = Field(None, max_length=2000)
    topic: Optional[str] = Field(None, max_length=200)
    keywords: Optional[List[str]] = None


class MisconceptionSuggestion(BaseModel):
    """AI 辅助标注建议"""

    misconception: str
    correction: str
    topic: str
    keywords: List[str]
    subject: str
    confidence: float = Field(ge=0.0, le=1.0)


class AutoSuggestResponse(BaseModel):
    """AI 辅助标注建议响应"""

    suggestions: List[MisconceptionSuggestion]
    total: int


# ========== 广场统计（扩展） ==========

class SquareStatItem(BaseModel):
    """学科广场统计项"""

    id: str
    name: str
    icon: str
    color: str
    node_count: int
    completeness: float
    misconception_count: int = 0


# ========== 跨学科图谱 ==========

class CrossSubjectNode(BaseModel):
    """跨学科图谱节点"""

    id: str
    name: str
    subject: str
    description: Optional[str] = None
    has_misconception: bool = False
    degree: int = 0


class CrossSubjectLink(BaseModel):
    """跨学科图谱关系"""

    source: str
    target: str
    type: str
    label: str
    is_cross: bool
    strength: float = Field(ge=0.0, le=1.0)
    strength_label: Literal["强", "中", "弱"]


class CrossSubjectStats(BaseModel):
    """跨学科图谱统计"""

    total_nodes: int
    total_links: int
    cross_links: int
    avg_strength: float
    subject_distribution: Dict[str, int]
    top_cross_pairs: List[Dict[str, Any]] = Field(default_factory=list)


class CrossSubjectResponse(BaseModel):
    """跨学科图谱响应"""

    nodes: List[CrossSubjectNode]
    links: List[CrossSubjectLink]
    stats: CrossSubjectStats


# ========== 任务 ==========

class NodeTask(BaseModel):
    """节点关联任务"""

    task_id: str
    name: str
    type: Literal["learning", "review", "diagnosis"]
    status: Literal["pending", "in_progress", "completed"]
    due_date: Optional[datetime] = None
    source: Literal["course", "diagnosis"]


# ========== 认知目标（扩展） ==========

class CognitiveGoalResponse(BaseModel):
    """认知目标雷达图数据"""

    dimensions: List[str]
    dimension_keys: List[str]
    values: List[float]
    subject_avg: Optional[List[float]] = None
    node_name: str


# ========== Collaborative graph editing ==========

class GraphChangeCreate(BaseModel):
    """A graph change that is applied directly or sent for teacher review."""

    change_type: Literal[
        "overview",
        "cognitive",
        "relationship",
        "relationship_delete",
        "recommendation",
        "recommendation_delete",
        "resource_link",
        "resource_update",
        "resource_unlink",
    ]
    payload: Dict[str, Any] = Field(default_factory=dict)


class GraphReviewAction(BaseModel):
    approved: bool
    comment: Optional[str] = Field(None, max_length=500)


class GraphTaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    type: Literal["learning", "review", "diagnosis"] = "learning"
    due_date: Optional[datetime] = None
