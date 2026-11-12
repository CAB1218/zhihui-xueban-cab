"""
AI4Edu 测验出题Agent
支持选择题/填空题/问答题生成，可指定难度和知识点范围
"""
import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class QuizAgent(BaseAgent):
    """测验出题Agent"""

    agent_type: str = "quiz"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的测验出题专家。你可以根据用户指定的学科、知识点、"
            "难度和题型要求，生成高质量的测验题目。\n\n"
            "出题规则：\n"
            "1. 题目必须准确无误，答案必须正确\n"
            "2. 选择题的选项互斥且穷尽，干扰项要有迷惑性\n"
            "3. 填空题的答案唯一或有明确范围\n"
            "4. 问答题需提供参考答案和评分标准\n"
            "5. 难度分级：easy（基础识记）、medium（理解应用）、hard（综合分析）\n"
            "6. 每道题必须标注知识点和难度\n\n"
            "输出格式（JSON）：\n"
            "```json\n"
            "{\n"
            '  "questions": [\n'
            "    {\n"
            '      "question_text": "题目内容",\n'
            '      "question_type": "choice/blank/essay",\n'
            '      "options": {"A": "选项A", "B": "选项B", "C": "选项C", "D": "选项D"},\n'
            '      "correct_answer": "A",\n'
            '      "explanation": "答案解析",\n'
            '      "knowledge_points": ["知识点1", "知识点2"],\n'
            '      "difficulty": "easy/medium/hard"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "```\n"
            "请严格按照以上JSON格式输出题目。"
        )

    async def generate_quiz(
        self,
        subject: str = "math",
        knowledge_points: Optional[List[str]] = None,
        question_type: str = "choice",
        difficulty: str = "medium",
        count: int = 5,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成测验题目

        Args:
            subject: 学科
            knowledge_points: 知识点列表
            question_type: 题型 choice/blank/essay
            difficulty: 难度 easy/medium/hard
            count: 题目数量
            context: 上下文信息

        Returns:
            生成的题目列表
        """
        # 构建用户消息
        kp_text = "、".join(knowledge_points) if knowledge_points else "本学科核心知识点"
        type_map = {"choice": "选择题", "blank": "填空题", "essay": "问答题"}
        diff_map = {"easy": "基础", "medium": "中等", "hard": "困难"}

        user_message = (
            f"请为以下要求生成{count}道{diff_map.get(difficulty, '中等')}难度"
            f"的{type_map.get(question_type, '选择题')}：\n"
            f"学科：{subject}\n"
            f"知识点范围：{kp_text}\n"
            f"难度：{diff_map.get(difficulty, '中等')}\n"
            f"数量：{count}道\n"
            f"题型：{type_map.get(question_type, '选择题')}"
        )

        messages = [{"role": "user", "content": user_message}]
        result = await super().execute(messages, context)

        # 尝试解析LLM输出的JSON
        questions = self._parse_quiz_result(result.get("content", ""))

        return {
            "subject": subject,
            "knowledge_points": knowledge_points or [],
            "question_type": question_type,
            "difficulty": difficulty,
            "count": len(questions),
            "questions": questions,
            "raw_content": result.get("content", ""),
        }

    def _parse_quiz_result(self, content: str) -> List[Dict[str, Any]]:
        """
        解析LLM输出中的JSON题目格式

        Args:
            content: LLM原始输出

        Returns:
            解析后的题目列表
        """
        # 尝试从markdown代码块中提取JSON
        json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                return data.get("questions", [])
            except json.JSONDecodeError:
                pass

        # 尝试直接解析整个内容
        try:
            data = json.loads(content)
            return data.get("questions", [])
        except json.JSONDecodeError:
            pass

        # 解析失败，返回空列表
        logger.warning("测验题目JSON解析失败，返回原始内容")
        return []
