"""
AI4Edu 知识图谱 Service
基于 Neo4j 实现知识图谱查询、BFS邻居发现、推荐、misconception管理、跨学科图谱等业务逻辑
所有 Cypher 查询均使用参数化以防止注入
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config import settings
from app.models.diagnosis import Diagnosis

logger = logging.getLogger(__name__)

# 12个学科分类
SUBJECT_CATEGORIES = [
    {"id": "math", "name": "数学", "icon": "DataAnalysis", "color": "#1976D2"},
    {"id": "physics", "name": "物理学", "icon": "Cpu", "color": "#F57C00"},
    {"id": "chemistry", "name": "化学", "icon": "MagicStick", "color": "#4CAF50"},
    {"id": "biology", "name": "生物学", "icon": "Grape", "color": "#388E3C"},
    {"id": "cs", "name": "计算机科学", "icon": "Monitor", "color": "#7B1FA2"},
    {"id": "chinese", "name": "语文", "icon": "Reading", "color": "#D32F2F"},
    {"id": "english", "name": "英语", "icon": "ChatDotRound", "color": "#00796B"},
    {"id": "history", "name": "历史", "icon": "Clock", "color": "#5D4037"},
    {"id": "geography", "name": "地理", "icon": "Place", "color": "#0288D1"},
    {"id": "politics", "name": "政治", "icon": "Stamp", "color": "#C62828"},
    {"id": "pe", "name": "体育", "icon": "TrophyBase", "color": "#FF6F00"},
    {"id": "art", "name": "艺术", "icon": "Brush", "color": "#AD1457"},
]

# ========== 完整度评分权重（v1 硬编码） ==========
W_DESCRIPTION = 0.20  # 描述填充率 20%
W_COGNITIVE = 0.20   # 认知水平填充率 20%
W_RELATION = 0.30    # 关系密度 30%
W_RESOURCE = 0.30    # 资源覆盖率 30%

# ========== 关系强度算法权重 ==========
W_COMMON_NEIGHBORS = 0.4
W_COMMON_RESOURCES = 0.3
W_REL_TYPE = 0.3

REL_TYPE_WEIGHTS: Dict[str, float] = {
    "PREREQUISITE": 1.0,
    "APPLICATION": 0.8,
    "RELATED": 0.5,
    "HAS_RESOURCE": 0.3,
}


def _strength_label(strength: float) -> str:
    """关系强度标签"""
    if strength >= 0.7:
        return "强"
    if strength >= 0.4:
        return "中"
    return "弱"


def _neo4j_safe_props(data: Dict[str, Any]) -> Dict[str, Any]:
    """把 dict / list 属性序列化为 JSON 字符串。

    Neo4j 只接受原始类型（及由原始类型构成的数组）作为属性值，
    直接写入 map 会抛 `Property values can only be of primitive types`。
    读取侧（如 cognitive_level）已按「字符串 → json.loads」处理。
    """
    safe: Dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            safe[key] = json.dumps(value, ensure_ascii=False)
        else:
            safe[key] = value
    return safe


class GraphService:
    """知识图谱服务"""

    def __init__(self):
        """初始化 Neo4j 驱动"""
        self._driver: Optional[AsyncDriver] = None
        self._subject_hierarchy_ready = False

    async def _get_driver(self) -> AsyncDriver:
        """获取 Neo4j 异步驱动（懒加载单例）"""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            )
        return self._driver

    async def close(self):
        """关闭驱动连接"""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def _run(self, cypher: str, params: Optional[Dict] = None) -> List[Dict]:
        """执行参数化 Cypher 查询并返回记录列表"""
        driver = await self._get_driver()
        async with driver.session() as session:
            result = await session.run(cypher, params or {})
            records = await result.data()
            return records

    # ==================== 图谱广场 ====================

    async def ensure_subject_hierarchy(self) -> None:
        """Ensure subjects and knowledge points are connected by graph edges."""
        if self._subject_hierarchy_ready:
            return

        await self._run(
            "UNWIND $subjects AS subject "
            "MERGE (s:Subject {id: 'subject_' + subject.id}) "
            "SET s.subject_id = subject.id, s.name = subject.name, "
            "s.icon = subject.icon, s.color = subject.color, s.node_type = 'subject' "
            "WITH s, subject "
            "OPTIONAL MATCH (n:KnowledgeNode {subject: subject.id}) "
            "FOREACH (_ IN CASE WHEN n IS NULL THEN [] ELSE [1] END | "
            "  MERGE (s)-[:HAS_KNOWLEDGE]->(n))",
            {"subjects": SUBJECT_CATEGORIES},
        )
        self._subject_hierarchy_ready = True

    async def get_subject_graph(self, subject_id: str) -> Dict[str, Any]:
        """Return a subject node, its knowledge points, and their relationships."""
        await self.ensure_subject_hierarchy()
        records = await self._run(
            "MATCH (s:Subject {subject_id: $subject_id}) "
            "OPTIONAL MATCH (s)-[:HAS_KNOWLEDGE]->(n:KnowledgeNode) "
            "WITH s, [node IN collect(DISTINCT n) WHERE node IS NOT NULL] AS knowledge_nodes "
            "OPTIONAL MATCH (a:KnowledgeNode)-[r:RELATED|PREREQUISITE|APPLICATION|RECOMMENDS]->"
            "(b:KnowledgeNode) "
            "WHERE a IN knowledge_nodes AND b IN knowledge_nodes "
            "RETURN s, knowledge_nodes, "
            "collect(DISTINCT {source: a.id, target: b.id, type: type(r), "
            "label: coalesce(r.label, type(r))}) AS knowledge_links",
            {"subject_id": subject_id},
        )
        if not records:
            return {"nodes": [], "links": []}

        subject = dict(records[0]["s"])
        knowledge_nodes = [
            {**dict(node), "node_type": "knowledge"}
            for node in records[0]["knowledge_nodes"]
        ]
        hierarchy_links = [
            {
                "source": subject["id"],
                "target": node["id"],
                "type": "HAS_KNOWLEDGE",
                "label": "包含知识点",
            }
            for node in knowledge_nodes
        ]
        knowledge_links = [
            link for link in records[0]["knowledge_links"]
            if link.get("source") and link.get("target")
        ]
        return {
            "nodes": [subject, *knowledge_nodes],
            "links": [*hierarchy_links, *knowledge_links],
        }

    async def get_square_stats(self, tenant_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取学科广场统计：每个学科的节点数、完整度和 misconception 计数
        """
        await self.ensure_subject_hierarchy()
        stats = []
        for subject in SUBJECT_CATEGORIES:
            # 统计该学科下的节点数
            count_result = await self._run(
                "MATCH (:Subject {subject_id: $subject})-[:HAS_KNOWLEDGE]->(n:KnowledgeNode) "
                "RETURN count(n) AS cnt",
                {"subject": subject["id"]},
            )
            node_count = count_result[0]["cnt"] if count_result else 0

            # 统计该学科下有 misconception 的节点数
            mc_result = await self._run(
                "MATCH (n:KnowledgeNode {subject: $subject}) "
                "WHERE n.has_misconception = true "
                "RETURN count(n) AS cnt",
                {"subject": subject["id"]},
            )
            misconception_count = mc_result[0]["cnt"] if mc_result else 0

            completeness = await self.calculate_completeness(subject["id"])

            stats.append({
                "id": subject["id"],
                "name": subject["name"],
                "icon": subject["icon"],
                "color": subject["color"],
                "node_count": node_count,
                "completeness": completeness,
                "misconception_count": misconception_count,
            })

        return stats

    async def calculate_completeness(self, subject: str) -> float:
        """
        计算某学科的知识图谱完整度（0-100）
        4维加权：描述填充率(20%) + 认知水平填充率(20%) + 关系密度(30%) + 资源覆盖率(30%)
        """
        # 节点总数
        node_result = await self._run(
            "MATCH (n:KnowledgeNode {subject: $subject}) RETURN count(n) AS cnt",
            {"subject": subject},
        )
        total_nodes = node_result[0]["cnt"] if node_result else 0
        if total_nodes == 0:
            return 0.0

        # 有描述的节点数
        desc_result = await self._run(
            "MATCH (n:KnowledgeNode {subject: $subject}) "
            "WHERE n.description IS NOT NULL AND n.description <> '' "
            "RETURN count(n) AS cnt",
            {"subject": subject},
        )
        desc_nodes = desc_result[0]["cnt"] if desc_result else 0

        # 有认知水平的节点数
        cog_result = await self._run(
            "MATCH (n:KnowledgeNode {subject: $subject}) "
            "WHERE n.cognitive_level IS NOT NULL AND n.cognitive_level <> '' "
            "RETURN count(n) AS cnt",
            {"subject": subject},
        )
        cog_nodes = cog_result[0]["cnt"] if cog_result else 0

        # 关系数（同学科内部关系）
        rel_result = await self._run(
            "MATCH (:KnowledgeNode {subject: $subject})-[r]->(:KnowledgeNode {subject: $subject}) "
            "RETURN count(r) AS cnt",
            {"subject": subject},
        )
        rel_count = rel_result[0]["cnt"] if rel_result else 0

        # 有 HAS_RESOURCE 关系的节点数
        res_result = await self._run(
            "MATCH (n:KnowledgeNode {subject: $subject})-[:HAS_RESOURCE]->(:Resource) "
            "RETURN count(DISTINCT n) AS cnt",
            {"subject": subject},
        )
        res_nodes = res_result[0]["cnt"] if res_result else 0

        # 4维加权计算
        description_fill_rate = desc_nodes / total_nodes
        cognitive_fill_rate = cog_nodes / total_nodes
        # 关系密度：期望每个节点至少2条关系
        relation_density = min(rel_count / (total_nodes * 2), 1.0) if total_nodes > 0 else 0.0
        resource_coverage = res_nodes / total_nodes if total_nodes > 0 else 0.0

        completeness = (
            description_fill_rate * W_DESCRIPTION * 100
            + cognitive_fill_rate * W_COGNITIVE * 100
            + relation_density * W_RELATION * 100
            + resource_coverage * W_RESOURCE * 100
        )

        return round(min(completeness, 100), 1)

    # ==================== 节点操作 ====================

    async def get_node_detail(self, node_id: str) -> Optional[Dict[str, Any]]:
        """获取节点详情"""
        result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) RETURN n",
            {"node_id": node_id},
        )
        if not result:
            return None
        return result[0]["n"]

    async def get_neighbors(self, node_id: str, depth: int = 1, limit: int = 50) -> Dict[str, Any]:
        """
        BFS 获取邻居节点和关系
        """
        # 获取目标节点
        node_result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) RETURN n",
            {"node_id": node_id},
        )
        if not node_result:
            return {"nodes": [], "links": []}

        # BFS 遍历邻居
        cypher = (
            "MATCH path = (start:KnowledgeNode {id: $node_id})-"
            "[:RELATED|PREREQUISITE|APPLICATION|RECOMMENDS*1..%d]-"
            "(neighbor:KnowledgeNode) "
            "RETURN DISTINCT neighbor, "
            "[rel in relationships(path) | {source: startNode(rel).id, target: endNode(rel).id, type: type(rel), label: rel.label}] AS rels "
            "LIMIT $limit"
        ) % depth

        records = await self._run(cypher, {"node_id": node_id, "limit": limit})

        nodes_map = {node_id: node_result[0]["n"]}
        links = []

        for record in records:
            neighbor = record["neighbor"]
            nodes_map[neighbor["id"]] = neighbor
            for rel in record["rels"]:
                link = {
                    "source": rel["source"],
                    "target": rel["target"],
                    "type": rel["type"],
                    "label": rel.get("label", rel["type"]),
                }
                # 去重
                if not any(l["source"] == link["source"] and l["target"] == link["target"] for l in links):
                    links.append(link)

        return {
            "nodes": list(nodes_map.values()),
            "links": links,
        }

    async def get_node_resources(self, node_id: str) -> List[Dict[str, Any]]:
        """获取节点关联资源"""
        result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id})-[:HAS_RESOURCE]->(r:Resource) RETURN r",
            {"node_id": node_id},
        )
        return [record["r"] for record in result]

    async def link_resource(self, node_id: str, resource: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create or refresh a resource projection in Neo4j and link it to a node."""
        result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) "
            "MERGE (r:Resource {id: $resource_id}) "
            "SET r.title = $title, r.description = $description, "
            "r.resource_type = $resource_type, r.mime_type = $mime_type, "
            "r.file_size = $file_size, r.url = $url, r.preview_url = $preview_url, "
            "r.uploader_id = $uploader_id, r.updated_at = $updated_at "
            "MERGE (n)-[:HAS_RESOURCE]->(r) RETURN r",
            {
                "node_id": node_id,
                "resource_id": str(resource.get("id")),
                "title": resource.get("title", ""),
                "description": resource.get("description") or "",
                "resource_type": resource.get("resource_type", "other"),
                "mime_type": resource.get("mime_type"),
                "file_size": resource.get("file_size"),
                "url": resource.get("url"),
                "preview_url": resource.get("preview_url"),
                "uploader_id": resource.get("uploader_id"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return result[0]["r"] if result else None

    async def unlink_resource(self, node_id: str, resource_id: int) -> bool:
        """Remove a resource association without deleting the shared resource node."""
        await self._run(
            "MATCH (:KnowledgeNode {id: $node_id})-[rel:HAS_RESOURCE]->"
            "(:Resource {id: $resource_id}) DELETE rel",
            {"node_id": node_id, "resource_id": str(resource_id)},
        )
        return True

    async def get_recommendations(self, node_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取推荐节点：基于同路径兄弟节点(50%) + 同学科相似节点(30%) + 跨学科关联节点(20%)
        """
        recommendations: List[Dict[str, Any]] = []
        seen_ids = {node_id}
        node_detail: Optional[Dict[str, Any]] = None

        # Teacher-curated recommendations always come first.
        manual_result = await self._run(
            "MATCH (:KnowledgeNode {id: $node_id})-[r:RECOMMENDS]->(recommended:KnowledgeNode) "
            "RETURN DISTINCT recommended, r.label AS reason LIMIT $limit",
            {"node_id": node_id, "limit": limit},
        )
        for record in manual_result:
            node = record["recommended"]
            if node["id"] not in seen_ids:
                node["_recommendation_reason"] = record.get("reason") or "教师推荐"
                node["_manual_recommendation"] = True
                recommendations.append(node)
                seen_ids.add(node["id"])

        if len(recommendations) >= limit:
            return recommendations[:limit]

        # 1. 同路径上的兄弟节点（50%配额）
        sibling_limit = max(1, int(limit * 0.5))
        sibling_result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id})-[:RELATED]->(parent)-[:RELATED]->(sibling:KnowledgeNode) "
            "WHERE sibling.id <> $node_id "
            "RETURN DISTINCT sibling "
            "LIMIT $limit",
            {"node_id": node_id, "limit": sibling_limit},
        )
        for record in sibling_result:
            node = record["sibling"]
            if node["id"] not in seen_ids:
                node["_recommendation_reason"] = "同路径兄弟节点"
                recommendations.append(node)
                seen_ids.add(node["id"])

        # 2. 同学科节点（30%配额）
        same_subject_limit = max(1, int(limit * 0.3))
        if len(recommendations) < limit:
            if node_detail is None:
                node_detail = await self.get_node_detail(node_id)
            if node_detail and node_detail.get("subject"):
                same_subject = await self._run(
                    "MATCH (n:KnowledgeNode {subject: $subject}) "
                    "WHERE n.id <> $node_id "
                    "RETURN n "
                    "LIMIT $extra_limit",
                    {
                        "subject": node_detail["subject"],
                        "node_id": node_id,
                        "extra_limit": same_subject_limit,
                    },
                )
                for record in same_subject:
                    node = record["n"]
                    if node["id"] not in seen_ids:
                        node["_recommendation_reason"] = "同学科相似节点"
                        recommendations.append(node)
                        seen_ids.add(node["id"])

        # 3. 跨学科关联节点（20%配额）
        cross_limit = max(1, limit - len(recommendations))
        if cross_limit > 0 and len(recommendations) < limit:
            if node_detail is None:
                node_detail = await self.get_node_detail(node_id)
            if node_detail and node_detail.get("subject"):
                cross_result = await self._run(
                    "MATCH (n:KnowledgeNode {id: $node_id})-[:RELATED|PREREQUISITE|APPLICATION]-(cross:KnowledgeNode) "
                    "WHERE cross.subject <> $subject AND cross.id <> $node_id "
                    "RETURN DISTINCT cross "
                    "LIMIT $limit",
                    {
                        "node_id": node_id,
                        "subject": node_detail["subject"],
                        "limit": cross_limit,
                    },
                )
                for record in cross_result:
                    node = record["cross"]
                    if node["id"] not in seen_ids:
                        node["_recommendation_reason"] = "跨学科关联节点"
                        recommendations.append(node)
                        seen_ids.add(node["id"])

        return recommendations[:limit]

    async def search_nodes(self, query: str, subject: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """
        搜索知识节点（参数化查询防注入）
        """
        if subject:
            result = await self._run(
                "MATCH (n:KnowledgeNode {subject: $subject}) "
                "WHERE n.name CONTAINS $query OR n.description CONTAINS $query "
                "RETURN n LIMIT $limit",
                {"subject": subject, "query": query, "limit": limit},
            )
        else:
            result = await self._run(
                "MATCH (n:KnowledgeNode) "
                "WHERE n.name CONTAINS $query OR n.description CONTAINS $query "
                "RETURN n LIMIT $limit",
                {"query": query, "limit": limit},
            )
        return [record["n"] for record in result]

    async def create_node(self, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建知识节点
        """
        # Neo4j 属性只支持原始类型/数组，dict、list 需序列化为 JSON 字符串
        # （cognitive_level 等在读取侧由 json.loads 还原）
        node_data = _neo4j_safe_props(node_data)
        # 学科既可以用 id（math）也可以用中文名（数学）传入，统一归一化为 id，
        # 否则会建出 subject_数学 这类与接口查询不一致的隐藏学科节点
        raw_subject = node_data.get("subject")
        subject = next(
            (
                item
                for item in SUBJECT_CATEGORIES
                if item["id"] == raw_subject or item["name"] == raw_subject
            ),
            {
                "id": str(raw_subject or "unknown"),
                "name": str(raw_subject or "unknown"),
                "icon": "Reading",
                "color": "#5B8FF9",
            },
        )
        node_data["subject"] = subject["id"]
        props = ", ".join(f"{k}: ${k}" for k in node_data.keys())
        cypher = (
            f"CREATE (n:KnowledgeNode {{{props}}}) "
            "WITH n MERGE (s:Subject {id: $subject_node_id}) "
            "SET s.subject_id = $subject_id, s.name = $subject_name, "
            "s.icon = $subject_icon, s.color = $subject_color, s.node_type = 'subject' "
            "MERGE (s)-[:HAS_KNOWLEDGE]->(n) RETURN n"
        )
        params = {
            **node_data,
            "subject_node_id": f"subject_{subject['id']}",
            "subject_id": subject["id"],
            "subject_name": subject["name"],
            "subject_icon": subject["icon"],
            "subject_color": subject["color"],
        }
        result = await self._run(cypher, params)
        return result[0]["n"] if result else {}

    async def update_node(self, node_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        更新知识节点属性
        """
        update_data = _neo4j_safe_props(update_data)
        set_clauses = ", ".join(f"n.{k} = ${k}" for k in update_data.keys())
        params = {"node_id": node_id, **update_data}
        cypher = f"MATCH (n:KnowledgeNode {{id: $node_id}}) SET {set_clauses} RETURN n"
        result = await self._run(cypher, params)
        return result[0]["n"] if result else None

    async def delete_node(self, node_id: str) -> bool:
        """Delete a knowledge node and dependent graph-only records."""
        existing = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) RETURN n.id AS id",
            {"node_id": node_id},
        )
        if not existing:
            return False

        await self._run(
            "MATCH (c:GraphChangeRequest)-[:TARGETS]->(:KnowledgeNode {id: $node_id}) "
            "DETACH DELETE c",
            {"node_id": node_id},
        )
        await self._run(
            "MATCH (:KnowledgeNode {id: $node_id})-[:HAS_TASK]->(t:GraphTask) "
            "DETACH DELETE t",
            {"node_id": node_id},
        )
        await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) DETACH DELETE n",
            {"node_id": node_id},
        )
        return True

    async def create_relationship(
        self, from_id: str, to_id: str, rel_type: str = "RELATED", label: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        创建节点间关系

        注意：Neo4j Cypher 不支持将关系类型作为参数传递，
        因此必须对 rel_type 进行白名单校验以防止 Cypher 注入。
        """
        import re
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", rel_type):
            raise ValueError(f"Invalid relationship type: {rel_type}. Must be UPPER_CASE_WITH_UNDERSCORES only.")

        params: Dict[str, Any] = {"from_id": from_id, "to_id": to_id, "label": label}
        if label:
            cypher = (
                "MATCH (a:KnowledgeNode {id: $from_id}), (b:KnowledgeNode {id: $to_id}) "
                f"MERGE (a)-[r:{rel_type}]->(b) SET r.label = $label "
                "RETURN type(r) AS rel_type, properties(r) AS props"
            )
        else:
            cypher = (
                "MATCH (a:KnowledgeNode {id: $from_id}), (b:KnowledgeNode {id: $to_id}) "
                f"MERGE (a)-[r:{rel_type}]->(b) RETURN type(r) AS rel_type, properties(r) AS props"
            )

        result = await self._run(cypher, params)
        if result:
            return {"type": result[0]["rel_type"], "props": result[0]["props"]}
        return None

    async def delete_relationship(self, from_id: str, to_id: str, rel_type: str = "RELATED") -> bool:
        """
        删除节点间关系

        注意：与 create_relationship 同理，rel_type 需白名单校验。
        """
        import re
        if not re.match(r"^[A-Z_][A-Z0-9_]*$", rel_type):
            raise ValueError(f"Invalid relationship type: {rel_type}. Must be UPPER_CASE_WITH_UNDERSCORES only.")

        await self._run(
            f"MATCH (a:KnowledgeNode {{id: $from_id}})-[r:{rel_type}]->(b:KnowledgeNode {{id: $to_id}}) DELETE r",
            {"from_id": from_id, "to_id": to_id},
        )
        return True

    # ==================== 认知目标 ====================

    async def get_cognitive_goals(self, node_id: str, include_avg: bool = False) -> Dict[str, Any]:
        """
        获取节点的认知目标雷达图数据
        六维：记忆(remember)、理解(understand)、应用(apply)、分析(analyze)、评价(evaluate)、创造(create)
        """
        node = await self.get_node_detail(node_id)
        if not node:
            return {}

        cognitive_level = node.get("cognitive_level", {})
        if isinstance(cognitive_level, str):
            try:
                cognitive_level = json.loads(cognitive_level)
            except (json.JSONDecodeError, TypeError):
                cognitive_level = {}

        # 六维数据（英文 key 存储，中文展示）
        dimensions = ["记忆", "理解", "应用", "分析", "评价", "创造"]
        dimension_keys = ["remember", "understand", "apply", "analyze", "evaluate", "create"]

        values = []
        for key in dimension_keys:
            val = cognitive_level.get(key, 0)
            if val is None:
                val = 0
            values.append(float(val))

        result: Dict[str, Any] = {
            "dimensions": dimensions,
            "dimension_keys": dimension_keys,
            "values": values,
            "node_name": node.get("name", ""),
        }

        # P1: 学科均值对比
        if include_avg and node.get("subject"):
            subject_avg = await self.get_subject_cognitive_avg(node["subject"])
            result["subject_avg"] = subject_avg
        else:
            result["subject_avg"] = None

        return result

    async def get_subject_cognitive_avg(self, subject: str) -> List[float]:
        """
        聚合同学科节点的认知水平均值
        返回六维均值列表 [remember_avg, understand_avg, ...]
        """
        result = await self._run(
            "MATCH (n:KnowledgeNode {subject: $subject}) "
            "WHERE n.cognitive_level IS NOT NULL AND n.cognitive_level <> '' "
            "RETURN n.cognitive_level AS cog",
            {"subject": subject},
        )

        dimension_keys = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
        sums = [0.0] * 6
        count = 0

        for record in result:
            cog = record.get("cog", {})
            if isinstance(cog, str):
                try:
                    cog = json.loads(cog)
                except (json.JSONDecodeError, TypeError):
                    cog = {}
            if not isinstance(cog, dict) or not cog:
                continue
            count += 1
            for i, key in enumerate(dimension_keys):
                val = cog.get(key, 0)
                if val is None:
                    val = 0
                sums[i] += float(val)

        if count == 0:
            return [0.0] * 6

        return [round(s / count, 1) for s in sums]

    # ==================== Misconception 管理 ====================

    async def get_misconceptions(self, node_id: str) -> List[Dict[str, Any]]:
        """获取节点的误解标注列表"""
        result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) RETURN n.misconceptions AS mc, n.has_misconception AS has_mc",
            {"node_id": node_id},
        )
        if not result:
            return []

        mc_raw = result[0].get("mc")
        if not mc_raw:
            return []

        if isinstance(mc_raw, str):
            try:
                return json.loads(mc_raw)
            except (json.JSONDecodeError, TypeError):
                return []
        elif isinstance(mc_raw, list):
            return mc_raw
        return []

    async def add_misconception(
        self, node_id: str, data: Dict[str, Any], user_id: int
    ) -> Dict[str, Any]:
        """
        添加误解标注
        生成 mc_id = "mc_" + uuid4()[:8]
        source 固定为 "teacher"（教师手动添加）
        """
        # 获取现有 misconceptions
        existing = await self.get_misconceptions(node_id)

        new_mc: Dict[str, Any] = {
            "mc_id": "mc_" + uuid.uuid4().hex[:8],
            "misconception": data.get("misconception", ""),
            "correction": data.get("correction", ""),
            "topic": data.get("topic", ""),
            "keywords": data.get("keywords", []),
            "source": "teacher",
            "annotated_by": user_id,
            "annotated_at": datetime.now(timezone.utc).isoformat(),
            "confidence": 1.0,
        }

        existing.append(new_mc)
        mc_json = json.dumps(existing, ensure_ascii=False)

        await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) "
            "SET n.misconceptions = $mc_json, n.has_misconception = true",
            {"node_id": node_id, "mc_json": mc_json},
        )

        return new_mc

    async def update_misconception(
        self, node_id: str, mc_id: str, data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """按 mc_id 定位更新误解标注"""
        existing = await self.get_misconceptions(node_id)

        found = False
        for item in existing:
            if item.get("mc_id") == mc_id:
                if "misconception" in data and data["misconception"] is not None:
                    item["misconception"] = data["misconception"]
                if "correction" in data and data["correction"] is not None:
                    item["correction"] = data["correction"]
                if "topic" in data and data["topic"] is not None:
                    item["topic"] = data["topic"]
                if "keywords" in data and data["keywords"] is not None:
                    item["keywords"] = data["keywords"]
                found = True
                break

        if not found:
            return None

        mc_json = json.dumps(existing, ensure_ascii=False)
        await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) "
            "SET n.misconceptions = $mc_json",
            {"node_id": node_id, "mc_json": mc_json},
        )

        # 返回更新后的项
        for item in existing:
            if item.get("mc_id") == mc_id:
                return item
        return None

    async def delete_misconception(self, node_id: str, mc_id: str) -> bool:
        """按 mc_id 删除误解标注，若数组为空则 has_misconception=false"""
        existing = await self.get_misconceptions(node_id)

        new_list = [item for item in existing if item.get("mc_id") != mc_id]
        if len(new_list) == len(existing):
            return False  # 未找到要删除的项

        mc_json = json.dumps(new_list, ensure_ascii=False)
        has_mc = len(new_list) > 0

        await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) "
            "SET n.misconceptions = $mc_json, n.has_misconception = $has_mc",
            {"node_id": node_id, "mc_json": mc_json, "has_mc": has_mc},
        )

        return True

    # ==================== 跨学科图谱 ====================

    async def get_cross_subject_graph(
        self,
        subjects: List[str],
        min_strength: float = 0.0,
        max_nodes: int = 100,
    ) -> Dict[str, Any]:
        """
        获取跨学科知识点关联网络
        返回节点、关系（含强度）和统计数据
        """
        await self.ensure_subject_hierarchy()

        # 1. 获取选定的学科节点和知识点节点
        subject_records = await self._run(
            "MATCH (s:Subject) WHERE s.subject_id IN $subjects "
            "RETURN s ORDER BY s.subject_id",
            {"subjects": subjects},
        )
        node_records = await self._run(
            "MATCH (n:KnowledgeNode) WHERE n.subject IN $subjects "
            "RETURN n.id AS id, n.name AS name, n.subject AS subject, "
            "n.description AS description, n.has_misconception AS has_misconception",
            {"subjects": subjects},
        )

        # 最大节点数包含学科节点，优先保留每个学科的中心节点
        knowledge_limit = max(0, max_nodes - len(subject_records))
        if len(node_records) > knowledge_limit:
            node_records = node_records[:knowledge_limit]

        node_ids = {r["id"] for r in node_records}
        nodes: List[Dict[str, Any]] = []

        for record in subject_records:
            subject_node = dict(record["s"])
            nodes.append({
                **subject_node,
                "subject": subject_node["subject_id"],
                "node_type": "subject",
                "description": "学科中心节点",
                "has_misconception": False,
                "degree": 0,
            })

        for r in node_records:
            nodes.append({
                "id": r["id"],
                "name": r.get("name", r["id"]),
                "subject": r.get("subject", ""),
                "node_type": "knowledge",
                "description": r.get("description"),
                "has_misconception": bool(r.get("has_misconception", False)),
                "degree": 0,
            })

        # 学科中心节点到知识点的结构关系始终展示，不受强度阈值影响
        hierarchy_links: List[Dict[str, Any]] = []
        for subject_record in subject_records:
            subject_node = dict(subject_record["s"])
            child_ids = [r["id"] for r in node_records if r.get("subject") == subject_node["subject_id"]]
            for child_id in child_ids:
                hierarchy_links.append({
                    "source": subject_node["id"],
                    "target": child_id,
                    "type": "HAS_KNOWLEDGE",
                    "label": "包含知识点",
                    "is_cross": False,
                    "strength": 1.0,
                    "strength_label": "强",
                })
            for node in nodes:
                if node["id"] == subject_node["id"]:
                    node["degree"] = len(child_ids)

        # 2. 获取选定学科内 + 跨学科的关系
        rel_records = await self._run(
            "MATCH (a:KnowledgeNode)-[r]->(b:KnowledgeNode) "
            "WHERE a.subject IN $subjects AND b.subject IN $subjects "
            "RETURN a.id AS source, b.id AS target, "
            "type(r) AS type, r.label AS label, "
            "a.subject AS source_subject, b.subject AS target_subject",
            {"subjects": subjects},
        )

        # 过滤只包含选定节点的关系
        raw_links: List[Dict[str, Any]] = []
        for r in rel_records:
            src = r["source"]
            tgt = r["target"]
            if src not in node_ids or tgt not in node_ids:
                continue
            is_cross = r["source_subject"] != r["target_subject"]
            raw_links.append({
                "source": src,
                "target": tgt,
                "type": r["type"],
                "label": r.get("label") or r["type"],
                "is_cross": is_cross,
                "source_subject": r["source_subject"],
                "target_subject": r["target_subject"],
            })

        # 3. 计算关系强度
        # 先收集每个节点的邻居和资源，用于批量计算共同邻居和共同资源
        node_neighbors: Dict[str, set] = {}
        node_resources: Dict[str, set] = {}

        for nid in node_ids:
            # 获取邻居
            nb_result = await self._run(
                "MATCH (n:KnowledgeNode {id: $nid})-[]-(m:KnowledgeNode) "
                "RETURN collect(DISTINCT m.id) AS neighbor_ids",
                {"nid": nid},
            )
            node_neighbors[nid] = set(nb_result[0]["neighbor_ids"]) if nb_result else set()

            # 获取资源
            res_result = await self._run(
                "MATCH (n:KnowledgeNode {id: $nid})-[:HAS_RESOURCE]->(r:Resource) "
                "RETURN collect(DISTINCT elementId(r)) AS resource_ids",
                {"nid": nid},
            )
            node_resources[nid] = set(res_result[0]["resource_ids"]) if res_result else set()

        # 计算每条关系的强度
        max_common_neighbors = 1
        max_common_resources = 1

        link_strengths: List[Dict[str, Any]] = []
        for link in raw_links:
            src = link["source"]
            tgt = link["target"]

            # 共同邻居数
            common_nb = len(node_neighbors.get(src, set()) & node_neighbors.get(tgt, set()))
            # 共同资源数
            common_res = len(node_resources.get(src, set()) & node_resources.get(tgt, set()))
            # 关系类型权重
            rel_type_weight = REL_TYPE_WEIGHTS.get(link["type"], 0.5)

            link_strengths.append({
                "link": link,
                "common_neighbors": common_nb,
                "common_resources": common_res,
                "rel_type_weight": rel_type_weight,
            })

            max_common_neighbors = max(max_common_neighbors, common_nb)
            max_common_resources = max(max_common_resources, common_res)

        # 归一化并计算最终强度
        links: List[Dict[str, Any]] = list(hierarchy_links)
        for ls in link_strengths:
            cn_norm = ls["common_neighbors"] / max_common_neighbors if max_common_neighbors > 0 else 0.0
            cr_norm = ls["common_resources"] / max_common_resources if max_common_resources > 0 else 0.0
            rt_weight = ls["rel_type_weight"]

            strength = W_COMMON_NEIGHBORS * cn_norm + W_COMMON_RESOURCES * cr_norm + W_REL_TYPE * rt_weight
            strength = round(min(max(strength, 0.0), 1.0), 2)

            # 按强度阈值过滤
            if strength < min_strength:
                continue

            link = ls["link"]
            link["strength"] = strength
            link["strength_label"] = _strength_label(strength)
            # 移除内部辅助字段
            link.pop("source_subject", None)
            link.pop("target_subject", None)
            links.append(link)

            # 更新节点 degree
            for node in nodes:
                if node["id"] == link["source"] or node["id"] == link["target"]:
                    node["degree"] += 1

        # 4. 计算统计数据
        cross_links = [l for l in links if l["is_cross"]]
        subject_distribution: Dict[str, int] = {}
        for node in nodes:
            if node.get("node_type") == "subject":
                continue
            subj = node["subject"]
            subject_distribution[subj] = subject_distribution.get(subj, 0) + 1

        avg_strength = round(sum(l["strength"] for l in links) / len(links), 2) if links else 0.0

        # Top 5 最强跨学科关系对
        cross_sorted = sorted(cross_links, key=lambda x: x["strength"], reverse=True)
        top_cross_pairs = [
            {
                "source": l["source"],
                "target": l["target"],
                "strength": l["strength"],
                "strength_label": l["strength_label"],
                "type": l["type"],
            }
            for l in cross_sorted[:5]
        ]

        stats = {
            "total_nodes": len(nodes),
            "total_links": len(links),
            "cross_links": len(cross_links),
            "avg_strength": avg_strength,
            "subject_distribution": subject_distribution,
            "top_cross_pairs": top_cross_pairs,
        }

        return {
            "nodes": nodes,
            "links": links,
            "stats": stats,
        }

    # ==================== Collaborative editing and review ====================

    async def create_change_request(
        self,
        node_id: str,
        change_type: str,
        payload: Dict[str, Any],
        submitted_by: int,
        tenant_id: Optional[int],
    ) -> Dict[str, Any]:
        """Store a student edit as a pending Neo4j review request."""
        request_id = "gcr_" + uuid.uuid4().hex[:12]
        created_at = datetime.now(timezone.utc).isoformat()
        result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) "
            "CREATE (c:GraphChangeRequest {"
            "id: $id, node_id: $node_id, change_type: $change_type, "
            "payload_json: $payload_json, status: 'pending', submitted_by: $submitted_by, "
            "tenant_id: $tenant_id, created_at: $created_at, updated_at: $created_at}) "
            "CREATE (c)-[:TARGETS]->(n) RETURN c",
            {
                "id": request_id,
                "node_id": node_id,
                "change_type": change_type,
                "payload_json": json.dumps(payload, ensure_ascii=False),
                "submitted_by": submitted_by,
                "tenant_id": tenant_id,
                "created_at": created_at,
            },
        )
        if not result:
            raise ValueError("Knowledge node does not exist")
        return self._deserialize_change_request(result[0]["c"])

    @staticmethod
    def _deserialize_change_request(item: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(item)
        raw_payload = data.pop("payload_json", "{}")
        try:
            data["payload"] = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
        except (json.JSONDecodeError, TypeError):
            data["payload"] = {}
        return data

    async def list_change_requests(
        self,
        status_filter: str = "pending",
        node_id: Optional[str] = None,
        tenant_id: Optional[int] = None,
        submitted_by: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        conditions = ["c.status = $status"]
        params: Dict[str, Any] = {"status": status_filter}
        if node_id:
            conditions.append("c.node_id = $node_id")
            params["node_id"] = node_id
        if tenant_id is not None:
            conditions.append("c.tenant_id = $tenant_id")
            params["tenant_id"] = tenant_id
        if submitted_by is not None:
            conditions.append("c.submitted_by = $submitted_by")
            params["submitted_by"] = submitted_by
        result = await self._run(
            "MATCH (c:GraphChangeRequest) WHERE " + " AND ".join(conditions) +
            " RETURN c ORDER BY c.created_at DESC",
            params,
        )
        return [self._deserialize_change_request(record["c"]) for record in result]

    async def get_change_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        result = await self._run(
            "MATCH (c:GraphChangeRequest {id: $request_id}) RETURN c",
            {"request_id": request_id},
        )
        return self._deserialize_change_request(result[0]["c"]) if result else None

    async def finish_change_request(
        self,
        request_id: str,
        status_value: str,
        reviewer_id: int,
        comment: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        result = await self._run(
            "MATCH (c:GraphChangeRequest {id: $request_id}) "
            "SET c.status = $status, c.reviewer_id = $reviewer_id, "
            "c.review_comment = $comment, c.updated_at = $updated_at RETURN c",
            {
                "request_id": request_id,
                "status": status_value,
                "reviewer_id": reviewer_id,
                "comment": comment,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return self._deserialize_change_request(result[0]["c"]) if result else None

    # ==================== Graph assignments ====================

    async def create_graph_task(
        self,
        node_id: str,
        data: Dict[str, Any],
        assigned_by: int,
        tenant_id: Optional[int],
    ) -> Optional[Dict[str, Any]]:
        task_id = "gt_" + uuid.uuid4().hex[:12]
        result = await self._run(
            "MATCH (n:KnowledgeNode {id: $node_id}) "
            "CREATE (n)-[:HAS_TASK]->(t:GraphTask {"
            "id: $task_id, name: $name, description: $description, type: $type, "
            "status: 'pending', due_date: $due_date, source: 'teacher', "
            "assigned_by: $assigned_by, tenant_id: $tenant_id, created_at: $created_at}) "
            "RETURN t",
            {
                "node_id": node_id,
                "task_id": task_id,
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "type": data.get("type", "learning"),
                "due_date": data.get("due_date"),
                "assigned_by": assigned_by,
                "tenant_id": tenant_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        return dict(result[0]["t"]) if result else None

    async def get_graph_tasks(self, node_id: str, tenant_id: Optional[int]) -> List[Dict[str, Any]]:
        result = await self._run(
            "MATCH (:KnowledgeNode {id: $node_id})-[:HAS_TASK]->(t:GraphTask) "
            "WHERE $tenant_id IS NULL OR t.tenant_id = $tenant_id RETURN t ORDER BY t.created_at DESC",
            {"node_id": node_id, "tenant_id": tenant_id},
        )
        return [
            {
                "task_id": record["t"].get("id"),
                "name": record["t"].get("name", ""),
                "description": record["t"].get("description", ""),
                "type": record["t"].get("type", "learning"),
                "status": record["t"].get("status", "pending"),
                "due_date": record["t"].get("due_date"),
                "source": record["t"].get("source", "teacher"),
                "assigned_by": record["t"].get("assigned_by"),
            }
            for record in result
        ]

    # ==================== 任务查询 ====================

    async def get_node_tasks(
        self,
        node_id: str,
        db_session: AsyncSession,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取节点关联任务
        数据来源：Diagnosis 表，通过 knowledge_points JSON 中的知识点名称匹配
        """
        # 获取节点名称用于匹配
        node = await self.get_node_detail(node_id)
        if not node:
            return []

        node_name = node.get("name", "")
        if not node_name:
            return []

        # 查询 Diagnosis 表，匹配 weaknesses/strengths 中包含节点名称的诊断
        # weaknesses 和 strengths 是 Text 类型存储 JSON
        query = select(Diagnosis).where(
            Diagnosis.weaknesses.contains(node_name)
            | Diagnosis.strengths.contains(node_name)
            | Diagnosis.recommendations.contains(node_name)
        )
        if user_id is not None:
            query = query.where(Diagnosis.user_id == user_id)

        result = await db_session.execute(query)
        diagnoses = result.scalars().all()

        tasks: List[Dict[str, Any]] = await self.get_graph_tasks(node_id, tenant_id)
        for diag in diagnoses:
            # 映射诊断状态到任务状态
            status_map = {
                "pending": "pending",
                "in_progress": "in_progress",
                "completed": "completed",
            }
            task_status = status_map.get(diag.status, "pending")

            # 映射诊断类型到任务类型
            type_map = {
                "knowledge": "diagnosis",
                "comprehensive": "review",
                "unit": "learning",
            }
            task_type = type_map.get(diag.diagnosis_type, "diagnosis")

            tasks.append({
                "task_id": f"diag_{diag.id}",
                "name": diag.title,
                "type": task_type,
                "status": task_status,
                "due_date": diag.completed_at.isoformat() if diag.completed_at else None,
                "source": "diagnosis",
            })

        return tasks


# 全局单例
graph_service = GraphService()
