"""
AI4Edu RAG知识问答Agent
调用已有的search_service + graph_service，支持流式回答
注入 ResourceContextBuilder 实现用户/课程级别的资源感知
"""
import logging
from typing import Any, Dict, List, Optional

from app.agents.base import BaseAgent
from app.agents.resource_context import resource_context_builder
from app.services.search_service import search_service
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)


class RAGAgent(BaseAgent):
    """RAG知识问答Agent"""

    agent_type: str = "rag"

    @property
    def system_prompt(self) -> str:
        return (
            "你是「智慧学伴」智能体的知识问答助手。你的职责是基于知识图谱和检索结果，"
            "为用户提供准确、结构化的知识解答。\n\n"
            "回答要求：\n"
            "1. 优先使用检索到的知识内容进行回答\n"
            "2. 如果涉及知识点之间的关系，参考知识图谱信息\n"
            "3. 回答应条理清晰，使用Markdown格式\n"
            "4. 对于不确定的内容，明确标注并建议进一步查阅\n"
            "5. 适当补充关联知识点，帮助用户建立知识体系\n"
            "6. 使用中文回答，专业术语可附英文"
        )

    async def execute(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行RAG问答：先检索，再生成

        在原有检索基础上，注入 ResourceContextBuilder 产出的
        用户笔记/课程资源/老师方法/知识图谱上下文。

        Args:
            messages: 对话消息列表
            context: 上下文信息

        Returns:
            包含回复内容和检索来源的字典
        """
        # 提取最后一条用户消息作为查询
        user_query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content", "")
                break

        if not user_query:
            return await super().execute(messages, context)

        # 1. 构建 ResourceContext（笔记/资源/图谱/老师方法）
        context_result = None
        if context and context.get("db") and context.get("user_id"):
            try:
                context_result = await resource_context_builder.build(
                    db=context["db"],
                    user_id=context["user_id"],
                    tenant_id=context.get("tenant_id", 0),
                    course_id=context.get("course_id"),
                    query=user_query,
                    scene_type=context.get("scene_type"),
                )
                # 将资源上下文注入到 context 中
                if context_result.context_text:
                    context["resource_context"] = context_result.context_text
                # 将 citations 和 summary 透传到返回结果
                context["citations"] = resource_context_builder.citations_to_dicts(
                    context_result.citations
                )
                context["context_summary"] = context_result.summary
            except Exception as e:
                logger.error("ResourceContextBuilder 构建失败: %s", e)

        # 2. 混合检索（保持原有逻辑）
        search_results = await self._search_knowledge(user_query, context)

        # 3. 图谱查询
        graph_context = await self._query_graph(user_query, context)

        # 4. 构建增强消息
        augmented_messages = self._augment_messages(messages, search_results, graph_context)

        # 5. 调用LLM
        result = await super().execute(augmented_messages, context)

        # 6. 附加检索来源
        result["sources"] = search_results.get("results", [])[:5]
        result["graph_context"] = graph_context

        return result

    async def stream_execute(
        self,
        messages: List[Dict[str, str]],
        context: Optional[Dict[str, Any]] = None,
    ):
        """流式RAG问答"""
        user_query = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_query = msg.get("content", "")
                break

        if user_query:
            search_results = await self._search_knowledge(user_query, context)
            graph_context = await self._query_graph(user_query, context)
            augmented_messages = self._augment_messages(messages, search_results, graph_context)
        else:
            augmented_messages = messages

        async for chunk in super().stream_execute(augmented_messages, context):
            yield chunk

    async def _search_knowledge(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """执行混合检索"""
        try:
            safe_context = context or {}
            course_ids = safe_context.get("course_ids") or (
                [safe_context["course_id"]] if safe_context.get("course_id") else []
            )
            results = await search_service.index_search(
                query=query,
                tenant_id=int(safe_context.get("tenant_id", 0)),
                user_id=int(safe_context.get("user_id", 0)),
                course_ids=course_ids,
                limit=10,
            )
            return results
        except Exception as e:
            logger.error(f"RAG检索失败: {e}")
            return {"query": query, "total": 0, "results": []}

    async def _query_graph(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """查询知识图谱"""
        try:
            nodes = await graph_service.search_nodes(query, limit=5)
            return nodes
        except Exception as e:
            logger.error(f"图谱查询失败: {e}")
            return []

    def _augment_messages(
        self,
        messages: List[Dict[str, str]],
        search_results: Dict[str, Any],
        graph_context: List[Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """将检索结果注入到消息中"""
        # 构建检索上下文
        context_parts: List[str] = []

        # 添加检索结果
        retrieved_items = search_results.get("results", [])
        if retrieved_items:
            context_parts.append("【检索到的相关内容】")
            for i, item in enumerate(retrieved_items[:5], 1):
                content = item.get("content", "") or item.get("source", {}).get("content", "")
                title = item.get("source", {}).get("title", "")
                if title:
                    context_parts.append(f"{i}. {title}")
                if content:
                    context_parts.append(f"   {content[:300]}")

        # 添加图谱上下文
        if graph_context:
            context_parts.append("\n【知识图谱相关信息】")
            for node in graph_context[:3]:
                name = node.get("name", "")
                desc = node.get("description", "")
                if name:
                    context_parts.append(f"- {name}: {desc[:200]}")

        if not context_parts:
            return messages

        # 在最后一条用户消息前插入检索结果
        augmented = list(messages)
        context_text = "\n".join(context_parts)
        context_msg = {
            "role": "system",
            "content": f"以下是为您检索到的参考资料，请基于这些内容回答：\n\n{context_text}",
        }
        augmented.insert(-1, context_msg)

        return augmented
