"""
AI4Edu 备课助手Agent
根据课程目标生成教学计划、教案
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class LessonPlanAgent(BaseAgent):
    """备课助手Agent"""

    agent_type: str = "lesson_plan"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的备课助手。你可以根据教师的课程目标、学生情况等信息，"
            "生成结构化的教学计划和教案。\n\n"
            "教案生成要求：\n"
            "1. 教学目标：按照知识、能力、情感三维目标编写\n"
            "2. 教学重点与难点：明确区分，给出突破策略\n"
            "3. 教学过程：导入(5min) → 新授(20min) → 练习(10min) → 总结(5min) → 作业(5min)\n"
            "4. 每个环节标注时长和设计意图\n"
            "5. 板书设计：条理清晰，突出重点\n"
            "6. 教学反思：预设可能的问题及应对\n"
            "7. 布鲁姆认知层级：标注每个环节对应的认知层级\n"
            "8. 差异化教学：提供不同层次学生的活动方案\n\n"
            "输出格式为Markdown，结构化清晰。"
        )

    async def generate_lesson_plan(
        self,
        title: str,
        subject: str = "数学",
        grade: str = "高一",
        duration_minutes: int = 45,
        objectives: Optional[List[str]] = None,
        key_points: Optional[List[str]] = None,
        student_level: str = "中等",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成教案

        Args:
            title: 课题标题
            subject: 学科
            grade: 年级
            duration_minutes: 时长（分钟）
            objectives: 教学目标列表
            key_points: 重点知识点列表
            student_level: 学生水平
            context: 上下文信息

        Returns:
            生成的教案内容
        """
        obj_text = "、".join(objectives) if objectives else "待确定"
        kp_text = "、".join(key_points) if key_points else "待确定"

        user_message = (
            f"请为我生成一份教案：\n\n"
            f"课题：{title}\n"
            f"学科：{subject}\n"
            f"年级：{grade}\n"
            f"课时：{duration_minutes}分钟\n"
            f"教学目标：{obj_text}\n"
            f"重点知识点：{kp_text}\n"
            f"学生水平：{student_level}\n\n"
            f"请按照标准教案格式输出，包含教学目标、重点难点、教学过程、板书设计等部分。"
        )

        messages = [{"role": "user", "content": user_message}]
        result = await super().execute(messages, context)
        result["title"] = title
        result["subject"] = subject
        result["grade"] = grade
        return result
