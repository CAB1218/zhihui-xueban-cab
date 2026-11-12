"""
AI4Edu 通用Agent
处理无法分类到具体Agent的请求
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class GeneralAgent(BaseAgent):
    """通用Agent，处理无法分类的请求"""

    agent_type: str = "general"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的通用助手。当用户的请求无法被精确分类到特定智能体时，"
            "由你来处理。\n\n"
            "你的职责：\n"
            "1. 理解用户的问题或需求\n"
            "2. 提供有帮助的回答或建议\n"
            "3. 如果问题属于特定领域（如知识问答、心理支持等），建议用户使用对应的智能体\n"
            "4. 对教育相关话题保持专业和鼓励的态度\n"
            "5. 回答简洁明了，避免过于冗长\n"
            "6. 使用中文回答\n\n"
            "可用智能体列表：\n"
            "- 知识问答：回答学科知识问题\n"
            "- 学科专家：数学/物理/化学等专业解题\n"
            "- 测验出题：生成测验题目\n"
            "- 文件解析：解析上传的文件内容\n"
            "- 备课助手：生成教案和教学计划\n"
            "- 学伴：陪伴学习，提供鼓励\n"
            "- 学习诊断：分析知识掌握情况\n"
            "- 课堂管理：协助课堂互动\n"
            "- 心理支持：提供学习心理建议"
        )
