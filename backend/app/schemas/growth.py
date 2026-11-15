"""
智慧学伴 学生成长档案 Schemas
评价 CRUD、时间线、仪表盘相关 Pydantic 模型
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 评价 CRUD Schemas
# ---------------------------------------------------------------------------

class EvaluationCreate(BaseModel):
    """创建评价请求"""

    student_id: int = Field(..., description="学生用户ID")
    course_id: Optional[int] = Field(None, description="关联课程ID(可选)")
    evaluation_type: str = Field(..., description="评价类型: overall/academic/attitude/improvement")
    rating: int = Field(..., ge=1, le=5, description="评分1-5星")
    content: str = Field(..., min_length=1, description="评价内容")
    suggestion: Optional[str] = Field(None, description="学习建议")
    is_visible: bool = Field(True, description="是否对学生可见")


class EvaluationUpdate(BaseModel):
    """更新评价请求"""

    evaluation_type: Optional[str] = Field(None, description="评价类型: overall/academic/attitude/improvement")
    rating: Optional[int] = Field(None, ge=1, le=5, description="评分1-5星")
    content: Optional[str] = Field(None, description="评价内容")
    suggestion: Optional[str] = Field(None, description="学习建议")
    is_visible: Optional[bool] = Field(None, description="是否对学生可见")


class EvaluationResponse(BaseModel):
    """评价响应"""

    id: int = Field(..., description="评价ID")
    student_id: int = Field(..., description="学生用户ID")
    teacher_id: int = Field(..., description="教师用户ID")
    teacher_name: str = Field(..., description="教师姓名")
    course_id: Optional[int] = Field(None, description="关联课程ID")
    course_name: Optional[str] = Field(None, description="课程名称")
    evaluation_type: str = Field(..., description="评价类型")
    rating: int = Field(..., description="评分1-5星")
    content: str = Field(..., description="评价内容")
    suggestion: Optional[str] = Field(None, description="学习建议")
    is_visible: bool = Field(..., description="是否对学生可见")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


# ---------------------------------------------------------------------------
# 时间线 Schemas
# ---------------------------------------------------------------------------

class TimelineItem(BaseModel):
    """时间线条目"""

    source: str = Field(..., description="数据来源: agent/diagnosis/note/flashcard/evaluation/course/resource/classroom")
    event_type: str = Field(..., description="事件类型")
    title: str = Field(..., description="标题")
    description: Optional[str] = Field(None, description="描述")
    timestamp: datetime = Field(..., description="事件时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="附加元数据")


# ---------------------------------------------------------------------------
# 仪表盘 Schemas
# ---------------------------------------------------------------------------

class DashboardStatCard(BaseModel):
    """仪表盘统计卡片"""

    key: str = Field(..., description="统计项标识")
    label: str = Field(..., description="统计项名称")
    value: int = Field(..., description="统计值")
    icon: Optional[str] = Field(None, description="图标名称")


class GrowthDashboard(BaseModel):
    """成长仪表盘"""

    stat_cards: List[DashboardStatCard] = Field(default_factory=list, description="统计卡片列表")
    weekly_activity: List[Dict[str, Any]] = Field(default_factory=list, description="近7天每日活动统计")
    subject_distribution: List[Dict[str, Any]] = Field(default_factory=list, description="学科分布")
    recent_evaluations: List[EvaluationResponse] = Field(default_factory=list, description="最近评价")
