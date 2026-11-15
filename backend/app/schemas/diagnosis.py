"""
智慧学伴 诊断Schema
DiagnosisCreate / DiagnosisResponse / AnswerSubmit / DiagnosisReport
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DiagnosisCreate(BaseModel):
    """启动诊断请求"""

    diagnosis_type: str = Field(
        "knowledge",
        description="诊断类型: knowledge/comprehensive/unit",
    )
    title: str = Field(..., description="诊断标题", min_length=1, max_length=200)
    course_id: Optional[int] = Field(None, description="课程ID")
    subject: Optional[str] = Field(None, description="学科")
    knowledge_points: Optional[List[str]] = Field(None, description="知识点范围")
    question_count: int = Field(10, description="题目数量", ge=5, le=50)
    difficulty_range: Optional[str] = Field(
        None,
        description="难度范围: easy/medium/hard 或 easy-medium 等",
    )


class DiagnosisResponse(BaseModel):
    """诊断响应"""

    id: int = Field(..., description="诊断ID")
    tenant_id: int = Field(..., description="租户ID")
    user_id: int = Field(..., description="用户ID")
    course_id: Optional[int] = Field(None, description="课程ID")
    diagnosis_type: str = Field(..., description="诊断类型")
    title: str = Field(..., description="诊断标题")
    status: str = Field(..., description="状态: pending/in_progress/completed")
    total_questions: int = Field(0, description="总题数")
    correct_count: int = Field(0, description="正确题数")
    score: Optional[float] = Field(None, description="得分")
    duration_seconds: Optional[int] = Field(None, description="用时(秒)")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    completed_at: Optional[datetime] = Field(None, description="完成时间")
    created_at: datetime = Field(..., description="创建时间")


class DiagnosisQuestionResponse(BaseModel):
    """诊断题目响应"""

    id: int = Field(..., description="题目ID")
    question_text: str = Field(..., description="题目内容")
    question_type: str = Field(..., description="题型: choice/blank/essay")
    options: Optional[Dict[str, str]] = Field(None, description="选项")
    difficulty: str = Field(..., description="难度")
    sort_order: int = Field(..., description="排序")


class AnswerSubmit(BaseModel):
    """提交答案请求"""

    answers: Dict[str, str] = Field(
        ...,
        description="答案映射，key为题目ID(str)，value为用户答案",
    )
    duration_seconds: Optional[int] = Field(None, description="用时(秒)")


class DiagnosisReport(BaseModel):
    """诊断报告"""

    diagnosis: DiagnosisResponse = Field(..., description="诊断基本信息")
    theta: float = Field(..., description="IRT能力值θ")
    theta_level: str = Field(..., description="能力等级")
    accuracy: float = Field(..., description="正确率(%)")
    knowledge_analysis: Dict[str, Any] = Field(
        default_factory=dict,
        description="知识点维度分析",
    )
    weaknesses: List[str] = Field(default_factory=list, description="知识弱点")
    strengths: List[str] = Field(default_factory=list, description="知识强项")
    recommendations: List[str] = Field(default_factory=list, description="学习建议")
    report_text: Optional[str] = Field(None, description="报告全文")
    report_url: Optional[str] = Field(None, description="报告文件URL")


class ReviewCardResponse(BaseModel):
    """复习卡片响应"""

    id: int = Field(..., description="卡片ID")
    front: str = Field(..., description="正面(问题)")
    back: str = Field(..., description="背面(答案)")
    knowledge_point: Optional[str] = Field(None, description="知识点")
    difficulty: str = Field(..., description="难度")
