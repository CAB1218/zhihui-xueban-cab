"""
智慧学伴 学习资源上下文构建器
按 user_id + course_id 检索用户笔记、课程资源、知识图谱节点、老师方法
组装为结构化上下文文本，返回引用来源列表
"""
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.note import Note
from app.models.resource import Resource
from app.models.teacher_method import TeacherMethod
from app.models.user import User
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """引用来源数据结构"""

    type: str  # "note" / "resource" / "teacher_method" / "graph_node"
    title: str
    source_url: str  # 前端跳转路径
    teacher_name: Optional[str] = None  # 仅 teacher_method 类型


@dataclass
class ContextResult:
    """资源上下文构建结果"""

    context_text: str = ""  # 注入到提示词的上下文文本
    citations: List[Citation] = field(default_factory=list)  # 引用来源列表
    summary: Dict[str, int] = field(default_factory=lambda: {
        "notes_count": 0,
        "resources_count": 0,
        "graph_nodes_count": 0,
        "teacher_methods_count": 0,
    })
    # 原始检索结果列表（供 API 端点返回分类列表）
    raw_notes: List[Dict[str, Any]] = field(default_factory=list)
    raw_resources: List[Dict[str, Any]] = field(default_factory=list)
    raw_graph_nodes: List[Dict[str, Any]] = field(default_factory=list)
    raw_teacher_methods: List[Dict[str, Any]] = field(default_factory=list)


class ResourceContextBuilder:
    """学习资源上下文构建器

    根据用户 ID、课程 ID、查询内容、场景类型，检索并组装
    学习资源上下文（笔记、资源、图谱节点、老师方法），
    返回结构化上下文文本和引用来源列表。
    """

    async def build(
        self,
        db: AsyncSession,
        user_id: int,
        tenant_id: int,
        course_id: Optional[int] = None,
        query: Optional[str] = None,
        scene_type: Optional[str] = None,
    ) -> ContextResult:
        """构建学习资源上下文

        检索流程:
        1. 用户笔记 → 最多5条
        2. 课程资源 → 最多5条
        3. 知识图谱节点 → 最多3个
        4. 老师方法 → 最多3条

        Args:
            db: 数据库异步会话
            user_id: 用户 ID
            tenant_id: 租户 ID
            course_id: 课程 ID（可选）
            query: 用户查询文本（可选）
            scene_type: 场景类型（可选）

        Returns:
            ContextResult: 包含上下文文本、引用列表、摘要
        """
        # 并行检索 4 类资源
        notes = await self._search_notes(db, user_id, tenant_id, course_id, query)
        resources = await self._search_resources(db, tenant_id, course_id, query)
        graph_nodes = await self._search_graph_nodes(query)
        teacher_methods = await self._search_teacher_methods(db, tenant_id, course_id, query)

        # 组装上下文文本
        context_text = self._build_context_text(notes, resources, graph_nodes, teacher_methods)

        # 构建引用来源
        citations = self._build_citations(notes, resources, graph_nodes, teacher_methods)

        # 构建摘要
        summary = {
            "notes_count": len(notes),
            "resources_count": len(resources),
            "graph_nodes_count": len(graph_nodes),
            "teacher_methods_count": len(teacher_methods),
        }

        logger.info(
            "ResourceContextBuilder.build 完成: 笔记=%d, 资源=%d, 图谱=%d, 老师方法=%d",
            len(notes), len(resources), len(graph_nodes), len(teacher_methods),
        )

        return ContextResult(
            context_text=context_text,
            citations=citations,
            summary=summary,
            raw_notes=notes,
            raw_resources=resources,
            raw_graph_nodes=graph_nodes,
            raw_teacher_methods=teacher_methods,
        )

    async def _search_notes(
        self,
        db: AsyncSession,
        user_id: int,
        tenant_id: int,
        course_id: Optional[int],
        query: Optional[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """检索用户笔记

        Args:
            db: 数据库会话
            user_id: 用户 ID
            tenant_id: 租户 ID
            course_id: 课程 ID（可选过滤）
            query: 查询文本（可选模糊匹配）
            limit: 最大返回条数

        Returns:
            笔记列表，每条包含 id, title, excerpt
        """
        try:
            conditions = [
                Note.owner_id == user_id,
                Note.tenant_id == tenant_id,
                Note.is_deleted == False,  # noqa: E712
            ]
            if course_id:
                conditions.append(Note.course_id == course_id)

            # 如果有查询文本，尝试模糊匹配标题或纯文本内容
            if query:
                search_pattern = f"%{query}%"
                conditions.append(
                    (Note.title.ilike(search_pattern))
                    | (Note.content_plain.ilike(search_pattern))
                )

            stmt = (
                select(Note)
                .where(and_(*conditions))
                .order_by(desc(Note.updated_at))
                .limit(limit)
            )
            result = await db.execute(stmt)
            notes = result.scalars().all()

            return [
                {
                    "id": n.id,
                    "title": n.title,
                    "excerpt": (n.content_plain or n.content or "")[:200],
                    "course_id": n.course_id,
                }
                for n in notes
            ]
        except Exception as e:
            logger.error("检索用户笔记失败: %s", e)
            return []

    async def _search_resources(
        self,
        db: AsyncSession,
        tenant_id: int,
        course_id: Optional[int],
        query: Optional[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """检索课程资源

        Args:
            db: 数据库会话
            tenant_id: 租户 ID
            course_id: 课程 ID（可选过滤）
            query: 查询文本（可选模糊匹配）
            limit: 最大返回条数

        Returns:
            资源列表，每条包含 id, title, resource_type, url
        """
        try:
            conditions = [
                Resource.tenant_id == tenant_id,
                Resource.is_active == True,  # noqa: E712
            ]
            if course_id:
                conditions.append(Resource.course_id == course_id)

            if query:
                search_pattern = f"%{query}%"
                conditions.append(
                    (Resource.title.ilike(search_pattern))
                    | (Resource.description.ilike(search_pattern))
                )

            stmt = (
                select(Resource)
                .where(and_(*conditions))
                .order_by(desc(Resource.updated_at))
                .limit(limit)
            )
            result = await db.execute(stmt)
            resources = result.scalars().all()

            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "resource_type": r.resource_type,
                    "url": r.url,
                    "description": (r.description or "")[:200],
                    "course_id": r.course_id,
                }
                for r in resources
            ]
        except Exception as e:
            logger.error("检索课程资源失败: %s", e)
            return []

    async def _search_graph_nodes(
        self,
        query: Optional[str],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """检索知识图谱节点（复用 graph_service）

        Args:
            query: 查询文本
            limit: 最大返回条数

        Returns:
            图谱节点列表，每条包含 node_id, name, description
        """
        if not query:
            return []
        try:
            nodes = await graph_service.search_nodes(query, limit=limit)
            return [
                {
                    "node_id": node.get("node_id") or node.get("id", ""),
                    "name": node.get("name", ""),
                    "description": (node.get("description", "") or "")[:200],
                    "subject": node.get("subject", ""),
                }
                for node in nodes
            ]
        except Exception as e:
            logger.error("检索知识图谱节点失败: %s", e)
            return []

    async def _search_teacher_methods(
        self,
        db: AsyncSession,
        tenant_id: int,
        course_id: Optional[int],
        query: Optional[str],
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """检索老师方法

        Args:
            db: 数据库会话
            tenant_id: 租户 ID
            course_id: 课程 ID（可选过滤）
            query: 查询文本（可选模糊匹配知识点/标题）
            limit: 最大返回条数

        Returns:
            老师方法列表，每条包含 id, title, content, teacher_name, source_url
        """
        try:
            conditions = [
                TeacherMethod.tenant_id == tenant_id,
                TeacherMethod.is_active == True,  # noqa: E712
            ]
            if course_id:
                conditions.append(TeacherMethod.course_id == course_id)

            if query:
                search_pattern = f"%{query}%"
                conditions.append(
                    (TeacherMethod.title.ilike(search_pattern))
                    | (TeacherMethod.content.ilike(search_pattern))
                    | (TeacherMethod.knowledge_points.ilike(search_pattern))
                )

            stmt = (
                select(TeacherMethod, User.nickname)
                .outerjoin(User, TeacherMethod.teacher_id == User.id)
                .where(and_(*conditions))
                .order_by(desc(TeacherMethod.updated_at))
                .limit(limit)
            )
            result = await db.execute(stmt)
            rows = result.all()

            methods = []
            for row in rows:
                method = row[0]
                teacher_name = row[1] if len(row) > 1 else ""
                methods.append({
                    "id": method.id,
                    "title": method.title,
                    "content": (method.content or "")[:500],
                    "method_type": method.method_type,
                    "knowledge_points": method.knowledge_points,
                    "source_resource_id": method.source_resource_id,
                    "source_url": method.source_url,
                    "teacher_name": teacher_name or "",
                    "subject": method.subject,
                })

            return methods
        except Exception as e:
            logger.error("检索老师方法失败: %s", e)
            return []

    def _build_context_text(
        self,
        notes: List[Dict[str, Any]],
        resources: List[Dict[str, Any]],
        graph_nodes: List[Dict[str, Any]],
        teacher_methods: List[Dict[str, Any]],
    ) -> str:
        """将检索结果组装为结构化上下文文本

        按优先级排列：
        1. 【老师方法】（最高优先级，附带使用指令）
        2. 【我的笔记】
        3. 【课程资源】
        4. 【知识图谱】

        Args:
            notes: 笔记列表
            resources: 资源列表
            graph_nodes: 图谱节点列表
            teacher_methods: 老师方法列表

        Returns:
            结构化上下文文本
        """
        parts: List[str] = []

        # 1. 老师方法（最高优先级）
        if teacher_methods:
            parts.append("【老师方法】请优先使用以下老师讲授的方法：")
            for i, method in enumerate(teacher_methods, 1):
                teacher_name = method.get("teacher_name", "")
                parts.append(
                    f"{i}. {method['title']}"
                    + (f"（{teacher_name}老师）" if teacher_name else "")
                )
                content = method.get("content", "")
                if content:
                    parts.append(f"   内容: {content[:300]}")
                kp = method.get("knowledge_points")
                if kp:
                    parts.append(f"   知识点: {kp}")
            parts.append("")

        # 2. 用户笔记
        if notes:
            parts.append("【我的笔记】")
            for i, note in enumerate(notes, 1):
                parts.append(f"{i}. {note['title']}")
                excerpt = note.get("excerpt", "")
                if excerpt:
                    parts.append(f"   摘要: {excerpt[:200]}")
            parts.append("")

        # 3. 课程资源
        if resources:
            parts.append("【课程资源】")
            for i, resource in enumerate(resources, 1):
                parts.append(
                    f"{i}. {resource['title']}（类型: {resource.get('resource_type', 'unknown')}）"
                )
                desc = resource.get("description", "")
                if desc:
                    parts.append(f"   描述: {desc[:200]}")
            parts.append("")

        # 4. 知识图谱
        if graph_nodes:
            parts.append("【知识图谱】")
            for i, node in enumerate(graph_nodes, 1):
                parts.append(f"{i}. {node.get('name', '')}")
                desc = node.get("description", "")
                if desc:
                    parts.append(f"   描述: {desc[:200]}")
            parts.append("")

        if not parts:
            return ""

        # 组装完整上下文
        context_text = "\n".join(parts)
        return (
            "以下是当前学生的学习资源上下文，请在回答时参考这些内容：\n\n"
            + context_text
        )

    def _build_citations(
        self,
        notes: List[Dict[str, Any]],
        resources: List[Dict[str, Any]],
        graph_nodes: List[Dict[str, Any]],
        teacher_methods: List[Dict[str, Any]],
    ) -> List[Citation]:
        """构建引用来源列表

        Args:
            notes: 笔记列表
            resources: 资源列表
            graph_nodes: 图谱节点列表
            teacher_methods: 老师方法列表

        Returns:
            Citation 对象列表
        """
        citations: List[Citation] = []

        # 老师方法引用（优先显示）
        for method in teacher_methods:
            source_url = method.get("source_url") or ""
            if not source_url and method.get("source_resource_id"):
                source_url = f"/resources/{method['source_resource_id']}"
            if not source_url:
                source_url = "#"
            citations.append(Citation(
                type="teacher_method",
                title=method.get("title", ""),
                source_url=source_url,
                teacher_name=method.get("teacher_name"),
            ))

        # 笔记引用
        for note in notes:
            citations.append(Citation(
                type="note",
                title=note.get("title", ""),
                source_url=f"/notes/{note.get('id', '')}",
            ))

        # 资源引用
        for resource in resources:
            citations.append(Citation(
                type="resource",
                title=resource.get("title", ""),
                source_url=f"/resources/{resource.get('id', '')}",
            ))

        # 图谱节点引用
        for node in graph_nodes:
            node_id = node.get("node_id") or node.get("name", "")
            citations.append(Citation(
                type="graph_node",
                title=node.get("name", ""),
                source_url=f"/graph/nodes/{node_id}",
            ))

        return citations

    def citations_to_dicts(self, citations: List[Citation]) -> List[Dict[str, Any]]:
        """将 Citation 列表转为字典列表（用于 JSON 序列化存储）

        Args:
            citations: Citation 对象列表

        Returns:
            字典列表
        """
        return [
            {
                "type": c.type,
                "title": c.title,
                "source_url": c.source_url,
                "teacher_name": c.teacher_name,
            }
            for c in citations
        ]


# 全局单例
resource_context_builder = ResourceContextBuilder()
