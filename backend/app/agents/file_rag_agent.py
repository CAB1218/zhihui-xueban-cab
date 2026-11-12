"""
AI4Edu 文件解析Agent
处理用户上传的PDF/Word/PPT，提取知识点并回答问题
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.services.file_parser import FileParser

logger = logging.getLogger(__name__)


class FileRAGAgent(BaseAgent):
    """文件解析Agent"""

    agent_type: str = "file_rag"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的文件解析助手。用户会上传文件（PDF/Word/PPT等），"
            "你需要基于文件内容回答用户的问题。\n\n"
            "回答要求：\n"
            "1. 严格基于文件内容回答，不要编造文件中没有的信息\n"
            "2. 引用文件内容时，注明所在章节或页码\n"
            "3. 如果用户问题超出文件范围，如实告知\n"
            "4. 帮助用户提取文件中的关键知识点\n"
            "5. 可以对文件内容进行总结、归纳和比较\n"
            "6. 如果文件内容较长，先概括要点再展开细节"
        )

    async def execute_with_file(
        self,
        user_question: str,
        file_content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        解析文件并回答问题

        Args:
            user_question: 用户关于文件的问题
            file_content: 文件二进制内容
            filename: 文件名
            mime_type: MIME类型
            context: 上下文信息

        Returns:
            回答结果
        """
        # 1. 解析文件
        parsed_text = await FileParser.parse_file(
            file_content, mime_type=mime_type, filename=filename
        )

        if not parsed_text or not parsed_text.strip():
            return {
                "content": f"无法解析文件 {filename}，请确认文件格式正确且内容非空。",
                "agent_type": self.agent_type,
                "filename": filename,
                "parsed_length": 0,
            }

        # 2. 构建增强消息
        truncated_text = parsed_text[:8000]  # 限制上下文长度
        file_context_msg = {
            "role": "system",
            "content": (
                f"以下是用户上传的文件 {filename} 的内容：\n\n"
                f"---文件内容开始---\n{truncated_text}\n---文件内容结束---\n\n"
                f"请基于以上文件内容回答用户的问题。"
            ),
        }
        user_msg = {"role": "user", "content": user_question}

        messages = [file_context_msg, user_msg]
        result = await super().execute(messages, context)
        result["filename"] = filename
        result["parsed_length"] = len(parsed_text)
        return result

    async def summarize_file(
        self,
        file_content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        生成文件摘要

        Args:
            file_content: 文件二进制内容
            filename: 文件名
            mime_type: MIME类型
            context: 上下文信息

        Returns:
            摘要结果
        """
        parsed_text = await FileParser.parse_file(
            file_content, mime_type=mime_type, filename=filename
        )

        if not parsed_text or not parsed_text.strip():
            return {
                "content": f"无法解析文件 {filename}",
                "agent_type": self.agent_type,
                "filename": filename,
            }

        truncated_text = parsed_text[:8000]
        messages = [
            {
                "role": "system",
                "content": "请为以下文件内容生成结构化摘要，包含：1.主题概述 2.核心要点 3.关键结论。",
            },
            {
                "role": "user",
                "content": f"文件名：{filename}\n\n文件内容：\n{truncated_text}",
            },
        ]

        result = await super().execute(messages, context)
        result["filename"] = filename
        result["parsed_length"] = len(parsed_text)
        return result

    async def extract_knowledge_points(
        self,
        file_content: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        从文件中提取知识点

        Args:
            file_content: 文件二进制内容
            filename: 文件名
            mime_type: MIME类型
            context: 上下文信息

        Returns:
            提取的知识点列表
        """
        parsed_text = await FileParser.parse_file(
            file_content, mime_type=mime_type, filename=filename
        )

        if not parsed_text or not parsed_text.strip():
            return {
                "content": "",
                "knowledge_points": [],
                "filename": filename,
            }

        truncated_text = parsed_text[:8000]
        messages = [
            {
                "role": "system",
                "content": (
                    "请从以下文件内容中提取知识点，以JSON数组格式输出。"
                    "每个知识点包含：name(名称)、description(描述)、level(认知层级：记忆/理解/应用/分析)。"
                    '示例：[{"name":"...", "description":"...", "level":"..."}]'
                ),
            },
            {
                "role": "user",
                "content": f"文件内容：\n{truncated_text}",
            },
        ]

        result = await super().execute(messages, context)
        result["filename"] = filename
        return result
