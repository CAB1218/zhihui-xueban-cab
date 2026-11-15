"""
智慧学伴 学伴服务
学伴对话、学习计划、进度追踪
"""
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.buddy_agent import BuddyAgent, PERSONALITY_PROMPTS
from app.core.exceptions import NotFoundException, ValidationException
from app.models.buddy import Buddy
from app.models.agent import AgentSession, AgentMessage

logger = logging.getLogger(__name__)

# 默认学伴名称
DEFAULT_BUDDY_NAMES: Dict[str, str] = {
    "encouraging": "小暖",
    "strict": "严老师",
    "humorous": "逗逗",
    "gentle": "柔柔",
}


class BuddyService:
    """学伴服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_or_create_profile(
        self,
        tenant_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        获取或创建学伴配置

        Args:
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            学伴信息
        """
        stmt = select(Buddy).where(Buddy.user_id == user_id)
        result = await self.db.execute(stmt)
        buddy = result.scalars().first()

        if not buddy:
            # 创建默认学伴
            default_personality = "encouraging"
            buddy = Buddy(
                tenant_id=tenant_id,
                user_id=user_id,
                name=DEFAULT_BUDDY_NAMES.get(default_personality, "小暖"),
                personality=default_personality,
                tone="friendly",
                interaction_mode="proactive",
                mood="happy",
                mood_score=80.0,
                experience_points=0,
                level=1,
            )
            self.db.add(buddy)
            await self.db.flush()

        return self._buddy_to_dict(buddy)

    async def update_profile(
        self,
        tenant_id: int,
        user_id: int,
        name: Optional[str] = None,
        personality: Optional[str] = None,
        tone: Optional[str] = None,
        interaction_mode: Optional[str] = None,
        avatar_url: Optional[str] = None,
        custom_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        更新学伴配置

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            name: 学伴名称
            personality: 人设
            tone: 语气
            interaction_mode: 互动模式
            avatar_url: 头像URL
            custom_prompt: 自定义提示词

        Returns:
            更新后的学伴信息
        """
        buddy_data = await self.get_or_create_profile(tenant_id, user_id)

        stmt = select(Buddy).where(Buddy.user_id == user_id)
        result = await self.db.execute(stmt)
        buddy = result.scalars().first()

        if not buddy:
            raise NotFoundException(message="学伴不存在")

        if name is not None:
            buddy.name = name
        if personality is not None:
            if personality not in PERSONALITY_PROMPTS:
                raise ValidationException(message=f"不支持的人设类型: {personality}")
            buddy.personality = personality
        if tone is not None:
            buddy.tone = tone
        if interaction_mode is not None:
            buddy.interaction_mode = interaction_mode
        if avatar_url is not None:
            buddy.avatar_url = avatar_url
        if custom_prompt is not None:
            buddy.custom_prompt = custom_prompt

        await self.db.flush()
        return self._buddy_to_dict(buddy)

    async def chat(
        self,
        tenant_id: int,
        user_id: int,
        message: str,
        session_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        与学伴对话

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            message: 用户消息
            session_id: 会话ID

        Returns:
            学伴回复
        """
        # 获取学伴信息
        buddy_data = await self.get_or_create_profile(tenant_id, user_id)
        personality = buddy_data.get("personality", "encouraging")

        # 调用学伴Agent
        agent = BuddyAgent(personality=personality)
        result = await agent.chat(
            message=message,
            context={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "buddy_name": buddy_data.get("name", ""),
                "buddy_level": buddy_data.get("level", 1),
            },
        )

        # 更新学伴经验值和等级
        stmt = select(Buddy).where(Buddy.user_id == user_id)
        db_result = await self.db.execute(stmt)
        buddy = db_result.scalars().first()
        if buddy:
            buddy.experience_points += 5
            new_level = buddy.experience_points // 100 + 1
            if new_level > buddy.level:
                buddy.level = new_level
            await self.db.flush()

        return {
            "content": result.get("content", ""),
            "personality": personality,
            "buddy_name": buddy_data.get("name", ""),
            "buddy_level": buddy_data.get("level", 1) if not buddy else buddy.level,
        }

    async def get_daily_report(
        self,
        tenant_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        获取每日学伴报告

        Args:
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            每日报告
        """
        buddy_data = await self.get_or_create_profile(tenant_id, user_id)

        # 简单统计（后续可接入ClickHouse）
        today = datetime.utcnow().date()
        report = {
            "date": today.isoformat(),
            "buddy_name": buddy_data.get("name", ""),
            "buddy_mood": buddy_data.get("mood", "happy"),
            "summary": f"今天是{today.strftime('%m月%d日')}，继续加油哦！",
            "learning_stats": {
                "questions_answered": 0,
                "notes_created": 0,
                "study_minutes": 0,
            },
            "encouragement": "每天进步一点点，积累起来就是大进步！",
        }

        return report

    async def get_mood(
        self,
        tenant_id: int,
        user_id: int,
    ) -> Dict[str, Any]:
        """
        获取学伴心情

        Args:
            tenant_id: 租户ID
            user_id: 用户ID

        Returns:
            学伴心情信息
        """
        buddy_data = await self.get_or_create_profile(tenant_id, user_id)

        return {
            "mood": buddy_data.get("mood", "happy"),
            "mood_score": buddy_data.get("mood_score", 80.0),
            "level": buddy_data.get("level", 1),
            "experience_points": buddy_data.get("experience_points", 0),
        }

    async def encourage(
        self,
        tenant_id: int,
        user_id: int,
        action: str = "praise",
    ) -> Dict[str, Any]:
        """
        与学伴互动（鼓励、点赞等）

        Args:
            tenant_id: 租户ID
            user_id: 用户ID
            action: 互动类型 praise/pet/high_five

        Returns:
            互动结果
        """
        buddy_data = await self.get_or_create_profile(tenant_id, user_id)

        # 调用学伴Agent获取鼓励语
        agent = BuddyAgent(personality=buddy_data.get("personality", "encouraging"))
        result = await agent.get_encouragement(
            achievement="和我互动" if action == "pet" else "",
            context={"tenant_id": tenant_id, "user_id": user_id},
        )

        # 更新心情
        stmt = select(Buddy).where(Buddy.user_id == user_id)
        db_result = await self.db.execute(stmt)
        buddy = db_result.scalars().first()
        if buddy:
            mood_boost = {"praise": 5, "pet": 3, "high_five": 4}.get(action, 3)
            buddy.mood_score = min(100.0, buddy.mood_score + mood_boost)
            buddy.mood = "happy" if buddy.mood_score >= 70 else "thinking"
            await self.db.flush()

        return {
            "content": result.get("content", ""),
            "action": action,
            "mood": buddy.mood if buddy else "happy",
            "mood_score": buddy.mood_score if buddy else 80.0,
        }

    def _buddy_to_dict(self, buddy: Buddy) -> Dict[str, Any]:
        """将Buddy模型转换为字典"""
        settings_data = {}
        if buddy.settings:
            try:
                settings_data = json.loads(buddy.settings)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": buddy.id,
            "tenant_id": buddy.tenant_id,
            "user_id": buddy.user_id,
            "name": buddy.name,
            "avatar_url": buddy.avatar_url,
            "personality": buddy.personality,
            "tone": buddy.tone,
            "interaction_mode": buddy.interaction_mode,
            "mood": buddy.mood,
            "mood_score": buddy.mood_score,
            "experience_points": buddy.experience_points,
            "level": buddy.level,
            "custom_prompt": buddy.custom_prompt,
            "settings": settings_data,
            "is_active": buddy.is_active,
            "created_at": buddy.created_at.isoformat() if buddy.created_at else None,
            "updated_at": buddy.updated_at.isoformat() if buddy.updated_at else None,
        }
