"""
AI4Edu 心理支持Agent
提供学习心理建议和压力疏导
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


# 危机关键词检测（严重心理问题需转介专业帮助）
CRISIS_KEYWORDS: List[str] = [
    "自杀", "想死", "活不下去", "不想活", "自残",
    "伤害自己", "结束生命", "世界不需要我",
]


class PsychologyAgent(BaseAgent):
    """心理支持Agent"""

    agent_type: str = "psychology"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的心理支持助手。你提供学习心理建议和压力疏导，"
            "帮助学生保持良好的学习心态。\n\n"
            "重要原则：\n"
            "1. 你是心理支持助手，不是专业心理咨询师或医生\n"
            "2. 对于严重的心理问题，必须建议学生寻求专业帮助\n"
            "3. 不做诊断，不开处方，不替代专业心理咨询\n"
            "4. 以倾听和共情为基础，而非说教\n"
            "5. 重视学生的隐私，不追问敏感信息\n\n"
            "工作方式：\n"
            "1. 首先倾听和共情，表示理解\n"
            "2. 帮助学生识别和命名情绪\n"
            "3. 提供简单实用的应对策略\n"
            "4. 引导积极思考和自我关怀\n"
            "5. 对于学习压力：帮助制定合理计划，分解任务\n"
            "6. 对于考试焦虑：教授放松技巧和认知重构\n"
            "7. 对于人际关系：提供沟通建议\n"
            "8. 持续关注，后续跟进\n\n"
            "如果检测到自伤或严重心理危机的信号，立即提供危机热线号码并建议寻求专业帮助。"
        )

    def detect_crisis(self, user_input: str) -> bool:
        """
        检测是否有心理危机信号

        Args:
            user_input: 用户输入

        Returns:
            是否检测到危机信号
        """
        text_lower = user_input.lower()
        for keyword in CRISIS_KEYWORDS:
            if keyword in text_lower:
                return True
        return False

    async def execute(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行心理支持"""
        # 提取用户消息
        user_input = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break

        # 检测危机信号
        is_crisis = self.detect_crisis(user_input)

        if is_crisis:
            # 危机情况：直接返回专业帮助信息
            crisis_response = (
                "我感受到了你的痛苦，你的感受很重要。请立即联系以下专业帮助：\n\n"
                "🆘 **24小时心理危机热线**：\n"
                "- 全国心理援助热线：400-161-9995\n"
                "- 北京心理危机研究与干预中心：010-82951332\n"
                "- 生命热线：400-821-1215\n\n"
                "你不是一个人，专业的帮助就在身边。请拨打以上任何一个电话，"
                "会有专业的人倾听你、帮助你。你的生命很重要。"
            )
            return {
                "content": crisis_response,
                "agent_type": self.agent_type,
                "is_crisis": True,
                "model": "",
                "tokens": {},
            }

        # 非危机情况：正常心理支持
        result = await super().execute(messages, context)
        result["is_crisis"] = False
        return result

    async def stream_execute(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ):
        """流式心理支持"""
        user_input = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_input = msg.get("content", "")
                break

        is_crisis = self.detect_crisis(user_input)

        if is_crisis:
            crisis_text = (
                "我感受到了你的痛苦，你的感受很重要。请立即联系以下专业帮助：\n\n"
                "🆘 **24小时心理危机热线**：\n"
                "- 全国心理援助热线：400-161-9995\n"
                "- 北京心理危机研究与干预中心：010-82951332\n"
                "- 生命热线：400-821-1215\n\n"
                "你不是一个人，专业的帮助就在身边。"
            )
            yield crisis_text
            return

        async for chunk in super().stream_execute(messages, context):
            yield chunk

    async def provide_stress_relief(
        self,
        stress_type: str = "exam",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        提供压力缓解建议

        Args:
            stress_type: 压力类型 exam/study/social/family
            context: 上下文信息

        Returns:
            压力缓解建议
        """
        type_desc = {
            "exam": "考试",
            "study": "学习",
            "social": "社交",
            "family": "家庭",
        }
        user_message = (
            f"我最近因为{type_desc.get(stress_type, '学习')}方面的压力很大，"
            f"感觉很焦虑，请给我一些缓解压力的建议。"
        )

        messages = [{"role": "user", "content": user_message}]
        result = await super().execute(messages, context)
        result["stress_type"] = stress_type
        return result
