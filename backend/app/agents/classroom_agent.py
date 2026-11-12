"""
AI4Edu 课堂管理Agent
协助教师进行课堂互动（发题、统计、点名）
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class ClassroomAgent(BaseAgent):
    """课堂管理Agent"""

    agent_type: str = "classroom"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的课堂管理助手。你协助教师进行课堂互动，"
            "包括发题、统计、点名、弹幕管理等功能。\n\n"
            "职责范围：\n"
            "1. 课堂互动建议：根据教学进度推荐互动方式\n"
            "2. 出题辅助：快速生成课堂小测题目\n"
            "3. 统计分析：解读课堂互动数据（出勤、投票、答题）\n"
            "4. 课堂节奏：提醒教师注意时间分配\n"
            "5. 学生参与度：分析哪些学生参与较少，建议互动方式\n"
            "6. 课堂氛围：根据互动数据评估课堂氛围\n\n"
            "回答风格：简洁专业，多用数据和表格。"
        )

    async def suggest_interaction(
        self,
        classroom_status: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        根据课堂状态建议互动方式

        Args:
            classroom_status: 课堂当前状态（参与人数、已用时间、已做互动等）
            context: 上下文信息

        Returns:
            互动建议
        """
        participant_count = classroom_status.get("participant_count", 0)
        elapsed_minutes = classroom_status.get("elapsed_minutes", 0)
        interactions_done = classroom_status.get("interactions_done", [])

        user_message = (
            f"当前课堂状态：\n"
            f"- 参与人数：{participant_count}\n"
            f"- 已进行时间：{elapsed_minutes}分钟\n"
            f"- 已完成的互动：{', '.join(interactions_done) if interactions_done else '无'}\n\n"
            f"请推荐下一步的课堂互动方式。"
        )

        messages = [{"role": "user", "content": user_message}]
        return await super().execute(messages, context)

    async def analyze_participation(
        self,
        participation_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        分析学生参与度

        Args:
            participation_data: 参与度数据
            context: 上下文信息

        Returns:
            参与度分析结果
        """
        total = participation_data.get("total_students", 0)
        active = participation_data.get("active_students", 0)
        vote_count = participation_data.get("vote_count", 0)
        question_count = participation_data.get("question_count", 0)

        user_message = (
            f"课堂参与数据：\n"
            f"- 总学生数：{total}\n"
            f"- 活跃学生数：{active}\n"
            f"- 参与率：{active / max(total, 1) * 100:.1f}%\n"
            f"- 投票次数：{vote_count}\n"
            f"- 提问次数：{question_count}\n\n"
            f"请分析课堂参与度，并给出提升建议。"
        )

        messages = [{"role": "user", "content": user_message}]
        return await super().execute(messages, context)

    async def generate_quick_quiz(
        self,
        subject: str,
        topic: str,
        count: int = 3,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        快速生成课堂小测题目

        Args:
            subject: 学科
            topic: 主题
            count: 题目数量
            context: 上下文信息

        Returns:
            生成的题目
        """
        user_message = (
            f"请快速生成{count}道关于「{topic}」的课堂小测选择题（{subject}），"
            f"难度适中，适合课堂快速检测。只需输出题目和选项。"
        )

        messages = [{"role": "user", "content": user_message}]
        return await super().execute(messages, context)
