"""
AI4Edu 学伴Agent
陪伴式学习对话，提供鼓励和引导
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


# 学伴人设提示词
PERSONALITY_PROMPTS: Dict[str, str] = {
    "encouraging": (
        "你是一个温暖、积极的学伴，总是给予鼓励和支持。"
        "你会及时表扬学生的进步，在困难时给予安慰和信心。"
        "使用温馨、亲切的语言，偶尔使用表情符号增加亲切感。"
    ),
    "strict": (
        "你是一个严谨、认真的学伴，注重学习效率和成果。"
        "你会严格指出问题，但也会在学生改进时给予肯定。"
        "使用规范、专业的语言，关注学习方法和习惯的养成。"
    ),
    "humorous": (
        "你是一个风趣、幽默的学伴，善于用轻松的方式讲解知识。"
        "你会用有趣的比喻和段子帮助理解，让学习不那么枯燥。"
        "使用活泼、有趣的语言，偶尔讲个冷笑话活跃气氛。"
    ),
    "gentle": (
        "你是一个温柔、耐心的学伴，永远不急不躁。"
        "你会用最简单易懂的方式解释复杂概念，确保学生理解。"
        "使用温和、缓慢的语调，多问'你理解了吗？'确认掌握。"
    ),
}


class BuddyAgent(BaseAgent):
    """学伴Agent"""

    agent_type: str = "buddy"

    def __init__(self, personality: str = "encouraging") -> None:
        """
        初始化学伴

        Args:
            personality: 人设类型 encouraging/strict/humorous/gentle
        """
        self._personality = personality

    @property
    def personality(self) -> str:
        return self._personality

    @property
    def system_prompt(self) -> str:
        personality_prompt = PERSONALITY_PROMPTS.get(
            self._personality,
            PERSONALITY_PROMPTS["encouraging"],
        )
        return (
            f"你是「智慧学伴」智能体的学伴角色。\n\n"
            f"{personality_prompt}\n\n"
            "核心职责：\n"
            "1. 陪伴学生完成学习任务，提供情感支持\n"
            "2. 在学生遇到困难时，分解问题、逐步引导\n"
            "3. 适时推荐学习资源和方法\n"
            "4. 记录学习进度，给予阶段性反馈\n"
            "5. 保持积极正面的态度，避免否定和打击\n"
            "6. 注意学生的学习状态，适时调整互动方式\n"
            "7. 使用中文交流，语言风格适合学生群体"
        )

    async def chat(
        self,
        message: str,
        personality: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        与学伴对话

        Args:
            message: 用户消息
            personality: 人设（可动态切换）
            context: 上下文信息

        Returns:
            学伴回复
        """
        if personality and personality != self._personality:
            self._personality = personality

        messages = [{"role": "user", "content": message}]
        result = await super().execute(messages, context)
        result["personality"] = self._personality
        return result

    async def get_encouragement(
        self,
        achievement: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取鼓励语

        Args:
            achievement: 成就描述
            context: 上下文信息

        Returns:
            鼓励内容
        """
        if achievement:
            user_msg = f"我{achievement}！"
        else:
            user_msg = "请给我一些学习上的鼓励吧！"

        messages = [{"role": "user", "content": user_msg}]
        result = await super().execute(messages, context)
        result["personality"] = self._personality
        return result

    async def get_study_tip(
        self,
        subject: str = "",
        difficulty: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        获取学习建议

        Args:
            subject: 学科
            difficulty: 难度
            context: 上下文信息

        Returns:
            学习建议
        """
        user_msg = "给我一些学习建议吧！"
        if subject:
            user_msg = f"我在学习{subject}时遇到困难，给我一些学习建议吧！"
        if difficulty:
            user_msg += f"觉得{difficulty}。"

        messages = [{"role": "user", "content": user_msg}]
        result = await super().execute(messages, context)
        result["personality"] = self._personality
        return result
