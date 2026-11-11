"""
AI4EDU 个性化学习建议服务（任务3：理解教学 — 个性化学习建议）

赛题要求与实现对应：
    结合学习要求            → 从任务1 的课程大纲里取「学习内容 + 要求 + 认知层次 + 教材出处」
    结合学情分析结果        → 复用任务2 的个体摘要（需巩固/基本掌握/证据不足 + 证据记录 ID）
    结合任务条件            → 周期（天）、教师指定关注点、学生画像
    明确建议内容            → 每条建议给出「学什么 / 怎么练 / 做什么活动」
    对应材料或练习          → 教材章节（取自大纲）+ 已上传资源 + 按规则登记的自建材料
    选择理由                → 每条建议引用具体证据（次数、正确率、记录 ID）与大纲要求
    必要的先后安排          → 按大纲单元顺序 + 大纲 connections（先修关系）拓扑排序，并分配到天
    回应发现的问题与需求    → 需巩固项逐条对应；证据不足项单独出「补充观察/练习」建议
    便于实施及教师调整      → 每条附验收标准与教师调整提示；整体附课堂共性提示
    涉及资源可追溯          → materials 里标 kind=textbook/resource/rule 与出处
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import CurriculumOutline
from app.models.resource import Resource
from app.services.learning_analysis_service import LearningAnalysisService, RecordView

# 知识点在「学情记录」与「课程大纲」里的叫法可能不一致，这里登记别名
TOPIC_ALIASES: Dict[str, List[str]] = {
    "哈希表": ["散列表", "哈希"],
    "散列表": ["哈希表"],
    "串与数组": ["串", "数组", "字符串"],
    "树的遍历": ["二叉树的遍历", "二叉树"],
    "图的遍历": ["图的遍历", "图"],
    "线性表": ["线性表", "顺序表", "链表"],
    "栈与队列": ["栈", "队列"],
    "复杂度": ["算法复杂度分析"],
}

# 认知层次权重：决定了「补到什么程度算够」
LEVEL_WEIGHT = {"了解": 1, "理解": 2, "掌握": 3, "运用": 4}

# 知识点 → 活动 / 内容提示（没有命中就走通用模板，保证任何知识点都能出建议）
KP_PLAYBOOK: Dict[str, Dict[str, Any]] = {
    "排序": {
        "activity": "手写插入排序对序列 [5, 2, 9, 1] 的每轮状态表，再对着代码逐步讲给同伴听；最后用同一组数据比较插入与选择排序的元素移动次数。",
        "content": [
            "先把「稳定 / 不稳定、时间复杂度、空间复杂度」三项指标记牢，后面所有算法都用这三把尺子比较",
            "逐个算法手动模拟：插入、选择、交换（冒泡/快排）、归并，每个至少手推一遍完整过程",
            "写出至少两种算法的代码并跑通，对照手推结果验证",
        ],
    },
    "查找": {
        "activity": "拿 10 个有序数字，手算折半查找的每次 mid 与比较次数，再与顺序查找比较，说明为什么有序能省一半。",
        "content": [
            "区分静态查找与动态查找，明确各自适用场景",
            "折半查找要能画出判定树，并说出平均查找长度怎么算",
            "二叉排序树 / 散列表至少掌握一种的实现思路与退化情况",
        ],
    },
    "图的遍历": {
        "activity": "给一张 6 个顶点的图，分别用 DFS 与 BFS 写出访问序列和栈/队列的变化过程，说明两者为什么结果不同。",
        "content": [
            "先固定图的存储方式（邻接矩阵 / 邻接表），再谈遍历，否则序列无法对齐",
            "DFS 用栈、BFS 用队列：把「容器变化」写出来，比背结论有效",
            "补一个连通分量判断的小例子，验证遍历的用途",
        ],
    },
    "树与二叉树": {
        "activity": "给一棵 7 个结点的二叉树，分别写出先序/中序/后序/层序遍历序列，再由两种序列反推树形。",
        "content": [
            "先掌握二叉树的性质（结点数、深度、满/完全二叉树），再做遍历",
            "四种遍历要能互相推导：由「先序+中序」唯一确定一棵树",
            "把递归写法与栈模拟对应起来，理解递归的本质",
        ],
    },
    "哈希表": {
        "activity": "用除留余数法把 8 个关键字插入长度为 11 的表，分别用线性探测与链地址法画出示意图，算平均查找长度。",
        "content": [
            "哈希函数设计 + 冲突处理是两件事，分开练",
            "线性探测要会算「堆积」带来的查找长度变化",
            "装填因子与扩容策略：说明为什么负载高时性能会掉",
        ],
    },
    "线性表": {
        "activity": "用数组和链表各实现一次「在第 i 个位置插入/删除」，记录两种实现分别移动/改指针多少次。",
        "content": [
            "先分清逻辑结构与存储结构，再谈操作代价",
            "顺序表重点练插入删除的元素移动次数与 O(n) 的来源",
            "单链表重点练指针改写顺序（先接后断），画图再写代码",
        ],
    },
    "栈与队列": {
        "activity": "用栈模拟括号匹配、用队列模拟银行叫号，各写 20 行以内的代码并跑通边界用例。",
        "content": [
            "先明确「操作受限的线性表」这个定位，再记栈顶/队头队尾规则",
            "循环队列要会判断队空队满（牺牲一个单元或加计数器）",
            "各记两个典型应用，说明为什么非它不可",
        ],
    },
    "串与数组": {
        "activity": "手算一次 KMP 的 next 数组（模式串 ababaca），再用暴力法对比比较次数。",
        "content": [
            "串的模式匹配先理解暴力法为什么慢，再看 next 数组省在哪",
            "数组重点练多维数组的地址计算（行优先 / 列优先）",
            "特殊矩阵压缩存储会算下标映射即可",
        ],
    },
}

GENERIC_PLAYBOOK: Dict[str, Any] = {
    "activity": "把这个知识点讲给同伴听（3 分钟），讲不通的地方就是没掌握的地方，记下来重点补。",
    "content": [
        "先复述该知识点的定义与适用场景，确认概念没有偏差",
        "再做 2 道例题并写出完整步骤，暴露过程中的断点",
        "最后总结一张「易错点清单」，作为复习时的检查表",
    ],
}


def _norm(text: str) -> str:
    """归一化：去掉空白与常见标点，便于宽松匹配"""
    return re.sub(r"[\s（）()、，,。；;：:·\-—_/]", "", text or "")


def _terms(kp: str) -> List[str]:
    terms = [kp] + TOPIC_ALIASES.get(kp, [])
    seen, out = set(), []
    for t in terms:
        n = _norm(t)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


class LearningAdviceService:
    """个性化学习建议生成"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.analysis = LearningAnalysisService(db)

    # ------------------------------------------------------------------
    # 数据获取
    # ------------------------------------------------------------------
    async def latest_outline(
        self, tenant_id: int, course_name: Optional[str]
    ) -> Optional[CurriculumOutline]:
        """取该课程最新一份梳理完成的大纲；没有匹配课程时退回最近一份"""
        base = select(CurriculumOutline).where(
            CurriculumOutline.tenant_id == tenant_id,
            CurriculumOutline.status == "completed",
        )
        if course_name:
            row = (
                await self.db.execute(
                    base.where(CurriculumOutline.course_query.ilike(f"%{course_name}%")).order_by(
                        CurriculumOutline.created_at.desc()
                    )
                )
            ).scalars().first()
            if row is not None:
                return row
        return (
            await self.db.execute(base.order_by(CurriculumOutline.created_at.desc()))
        ).scalars().first()

    async def course_resources(
        self, tenant_id: int, course_id: Optional[int]
    ) -> List[Resource]:
        stmt = select(Resource).where(
            Resource.tenant_id == tenant_id,
            Resource.is_active.is_(True),
            Resource.deleted_at.is_(None),
        )
        if course_id:
            stmt = stmt.where(Resource.course_id == course_id)
        stmt = stmt.order_by(Resource.created_at.desc()).limit(60)
        return list((await self.db.execute(stmt)).scalars().all())

    async def _course_weak_stats(
        self, records: Sequence[RecordView], kp: str
    ) -> Optional[Dict[str, Any]]:
        """算出该知识点在班级层面的薄弱比例，用于「是否课堂统一讲评」的建议"""
        by_student: Dict[int, List[RecordView]] = {}
        for r in records:
            if r.knowledge_point and r.judgeable and r.knowledge_point == kp:
                by_student.setdefault(r.student_id, []).append(r)
        if not by_student:
            return None
        weak = 0
        for recs in by_student.values():
            if len(recs) < 3:
                continue
            acc = sum(1 for x in recs if x.correct) / len(recs)
            if acc < 0.6:
                weak += 1
        total = len(by_student)
        return {
            "students_practiced": total,
            "weak_students": weak,
            "weak_ratio": round(weak / total, 4) if total else 0.0,
        }

    # ------------------------------------------------------------------
    # 大纲匹配
    # ------------------------------------------------------------------
    def _match_outline(self, kp: str, outline: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """把「学情里的知识点」对到大纲里的「学习内容」

        先按内容标题匹配（最精确），没有再退化到单元名匹配，都匹配不到就返回空，
        由调用方走「规则模板 + 明确说明未匹配到大纲」的分支，而不是硬编一个要求。
        """
        empty = {"matched": False, "unit": None, "unit_index": None, "contents": [], "textbook_ref": None, "match_term": None}
        if not outline:
            return empty
        units = outline.get("units") or []
        terms = _terms(kp)

        best_content: Optional[Tuple[int, int, Dict[str, Any], Dict[str, Any], str]] = None
        best_unit: Optional[Tuple[int, int, Dict[str, Any]]] = None

        for ui, unit in enumerate(units):
            unit_name = _norm(unit.get("name", ""))
            for term in terms:
                if not unit_name:
                    continue
                # 单元名与知识点同名（如「排序」「图」）优先级最高，
                # 否则「排序」会被「拓扑排序与关键路径」这类子串抢走
                if unit_name == term:
                    score = 100
                elif term in unit_name:
                    score = 75
                else:
                    continue
                if best_unit is None or score > best_unit[0]:
                    best_unit = (score, ui, unit)
            for content in unit.get("contents") or []:
                topic = _norm(content.get("topic", ""))
                if not topic:
                    continue
                for term in terms:
                    if topic == term:
                        score = 95
                    elif topic.startswith(term):
                        score = 80
                    elif term in topic:
                        score = 65
                    elif topic in term and len(topic) >= 3:
                        score = 60
                    else:
                        continue
                    if best_content is None or score > best_content[0]:
                        best_content = (score, ui, unit, content, term)

        # 单元级匹配可能比内容级更贴切（同名的整章 vs 别处的子串命中），按分数取高者
        if best_unit and (best_content is None or best_unit[0] >= best_content[0]):
            best_content = None

        if best_content:
            score, ui, unit, content, term = best_content
            return {
                "matched": True,
                "match_level": "content",
                "score": score,
                "unit": unit,
                "unit_index": ui,
                "content_index": (unit.get("contents") or []).index(content),
                "contents": [content],
                "textbook_ref": unit.get("textbook_ref"),
                "match_term": term,
            }

        if best_unit:
            score, ui, unit = best_unit
            contents = list(unit.get("contents") or [])
            # 单元级匹配时挑 2 个「要求最高、学时最多」的核心内容，避免一次推整章
            contents.sort(
                key=lambda c: (
                    -(c.get("suggested_hours") or 1),
                    -LEVEL_WEIGHT.get(c.get("requirement_level", "理解"), 2),
                )
            )
            picked = contents[:2]
            first_idx = (unit.get("contents") or []).index(picked[0]) if picked else 0
            return {
                "matched": True,
                "match_level": "unit",
                "score": score,
                "unit": unit,
                "unit_index": ui,
                "content_index": first_idx,
                "contents": picked,
                "textbook_ref": unit.get("textbook_ref"),
                "match_term": _norm(unit.get("name", "")),
            }

        return empty

    def _prerequisites(
        self, contents: Sequence[Dict[str, Any]], outline: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """从大纲 connections 找出这些内容的前置知识（用于解释先后安排）"""
        if not outline:
            return []
        topics = {_norm(c.get("topic", "")) for c in contents if c.get("topic")}
        out: List[Dict[str, str]] = []
        for conn in outline.get("connections") or []:
            to_topic = _norm(conn.get("to_topic", ""))
            if to_topic in topics:
                out.append(
                    {
                        "from_topic": conn.get("from_topic", ""),
                        "to_topic": conn.get("to_topic", ""),
                        "description": conn.get("description", ""),
                    }
                )
        return out[:3]

    # ------------------------------------------------------------------
    # 建议条目
    # ------------------------------------------------------------------
    def _practice_plan(self, kp: str, accuracy: Optional[float], level: str) -> List[Dict[str, Any]]:
        base = 5 if accuracy is None or accuracy >= 0.4 else 8
        return [
            {
                "stage": "诊断",
                "count": base,
                "desc": f"「{kp}」单点基础题（{level}层次），限时 {base * 3} 分钟",
                "pass_line": f"正确 ≥ {math.ceil(base * 0.6)} 题，否则先回看例题",
            },
            {
                "stage": "变式",
                "count": 10,
                "desc": "同知识点变式题：换数据、换问法、正反问各一组",
                "pass_line": "正确 ≥ 8 题（80%），才进入下一步",
            },
            {
                "stage": "综合",
                "count": 3,
                "desc": "与前置知识组合的综合题（如排序 + 复杂度分析）",
                "pass_line": "能写出完整步骤，≥2 题正确",
            },
        ]

    def _materials(
        self,
        kp: str,
        outline_match: Dict[str, Any],
        resources: Sequence[Resource],
    ) -> List[Dict[str, Any]]:
        """材料清单：教材章节（大纲出处）+ 已上传资源 + 按规则登记的自建材料"""
        out: List[Dict[str, Any]] = []
        if outline_match.get("textbook_ref"):
            out.append(
                {
                    "kind": "textbook",
                    "title": outline_match["textbook_ref"],
                    "detail": f"对应大纲内容：{'、'.join(c.get('topic', '') for c in outline_match['contents'])}",
                    "source": "课程大纲",
                }
            )

        key = _norm(kp)
        matched_res = [
            r
            for r in resources
            if key and (key in _norm(r.title) or key in _norm(r.description or "") or key in _norm(r.tags or ""))
        ][:3]
        for r in matched_res:
            out.append(
                {
                    "kind": "resource",
                    "resource_id": r.id,
                    "title": r.title,
                    "detail": (r.description or "")[:80],
                    "resource_type": r.resource_type,
                    "source": "资源库",
                }
            )

        out.append(
            {
                "kind": "rule",
                "title": f"「{kp}」错题重练卷",
                "detail": "从该生历史作答中筛出该知识点的错题重做，不足 10 题时按同知识点模板补齐",
                "rule": "筛选条件：knowledge_point={kp} 且 is_correct=false，按时间倒序，上限 10 题".format(kp=kp),
                "source": "按规则登记",
            }
        )
        out.append(
            {
                "kind": "rule",
                "title": f"「{kp}」分层自测卷（5+10+3）",
                "detail": "按本方案的诊断/变式/综合三段题量生成，难度取该生近 30 天正确率 ±10% 区间",
                "rule": "题量 5/10/3；难度带 = 该生正确率 ±0.1；题型按大纲认知层次取「理解/掌握/运用」",
                "source": "按规则登记",
            }
        )
        return out

    def _build_item(
        self,
        order: int,
        kp_row: Dict[str, Any],
        outline_match: Dict[str, Any],
        outline: Optional[Dict[str, Any]],
        resources: Sequence[Resource],
        class_stats: Optional[Dict[str, Any]],
        focus: Optional[str],
    ) -> Dict[str, Any]:
        kp = kp_row["knowledge_point"]
        accuracy = kp_row.get("accuracy")
        playbook = KP_PLAYBOOK.get(kp, GENERIC_PLAYBOOK)
        contents = outline_match.get("contents") or []
        requirements = [c.get("requirement") for c in contents if c.get("requirement")]
        levels = [c.get("requirement_level") or "理解" for c in contents]
        goal_level = levels[0] if levels else "掌握"
        hours = sum((c.get("suggested_hours") or 1) for c in contents) or 2.0

        # 目标：优先用大纲里写明的「学习要求」，没有就按认知层次生成可检查的表述
        if requirements:
            goal = f"达到大纲要求「{requirements[0]}」"
        else:
            goal = f"能独立完成「{kp}」的 {goal_level} 层次任务：说出定义与适用场景，并正确完成典型题"

        reason_parts = [
            f"学情依据：{kp_row.get('evidence_text')}（判定为{kp_row.get('status_label')}）",
        ]
        if requirements:
            reason_parts.append(f"课程要求：大纲写着「{requirements[0]}」（{goal_level}）")
        else:
            reason_parts.append("课程要求：现有大纲未收录该知识点，按通用「概念—过程—应用」路径补强")
        if class_stats and class_stats.get("weak_ratio", 0) >= 0.5:
            reason_parts.append(
                f"班级共性：该知识点 {class_stats['students_practiced']} 名有作答记录的学生中 "
                f"{class_stats['weak_students']} 名薄弱（{class_stats['weak_ratio'] * 100:.0f}%），属于共性问题，课堂讲评后个性化练习更省时"
            )
        if focus and _norm(focus) in _norm(kp):
            reason_parts.append(f"教师指定：本次优先补强「{focus}」")

        prereq = self._prerequisites(contents, outline)
        minutes = max(25, min(60, int(hours * 18)))
        item = {
            "order": order,
            "knowledge_point": kp,
            "status": kp_row.get("status"),
            "status_label": kp_row.get("status_label"),
            "accuracy": accuracy,
            "problem": f"{kp_row.get('evidence_text')}，判定为「{kp_row.get('status_label')}」",
            "evidence": {
                "attempts": kp_row.get("attempts"),
                "correct_count": kp_row.get("correct_count"),
                "accuracy": accuracy,
                "record_ids": kp_row.get("evidence_record_ids", []),
                "text": kp_row.get("evidence_text"),
            },
            "goal": goal,
            "goal_level": goal_level,
            "outline": {
                "matched": outline_match.get("matched", False),
                "unit": (outline_match.get("unit") or {}).get("name"),
                "unit_index": outline_match.get("unit_index"),
                "content_index": outline_match.get("content_index"),
                "topics": [c.get("topic") for c in contents],
                "requirements": requirements,
                "textbook_ref": outline_match.get("textbook_ref"),
                "hours": hours,
            },
            "content": playbook["content"],
            "practices": self._practice_plan(kp, accuracy, goal_level),
            "activity": playbook["activity"],
            "materials": self._materials(kp, outline_match, resources),
            "reason": "；".join(reason_parts),
            "prerequisites": prereq,
            "order_reason": (
                f"先学「{prereq[0]['from_topic']}」再练「{prereq[0]['to_topic']}」：{prereq[0]['description']}"
                if prereq
                else "按课程大纲的单元顺序安排，前面单元是后面内容的基础"
            ),
            "estimated_minutes": minutes,
            "acceptance": f"变式题 10 题正确 ≥ 8 题（80%），或再测 5 题正确 ≥ 4 题；未达标则重复本步练习，不进入下一步",
            "teacher_tip": "",
            "adjustable": ["题量", "难度", "完成时间", "是否改为小组活动"],
        }
        # 文案里要用到真实题量，等 practices 生成后再拼
        item["teacher_tip"] = (
            f"若「{kp}」已在课堂统一讲过，可把诊断题从 {item['practices'][0]['count']} 题减到 3 题，"
            "把时间留给变式题；若学生基础极弱，则把变式题拆成两组、中间插入一次讲评。"
        )
        return item

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    async def build_plan(
        self,
        *,
        tenant_id: int,
        student: Dict[str, Any],
        course: Dict[str, Any],
        records: Sequence[RecordView],
        cohort_records: Optional[Sequence[RecordView]] = None,
        duration_days: int = 7,
        focus: Optional[str] = None,
    ) -> Dict[str, Any]:
        course_id = course.get("id")
        course_name = course.get("name")

        outline_row = await self.latest_outline(tenant_id, course_name)
        outline: Optional[Dict[str, Any]] = None
        outline_meta: Dict[str, Any] = {"available": False}
        if outline_row and outline_row.outline:
            try:
                outline = json.loads(outline_row.outline)
                outline_meta = {
                    "available": True,
                    "outline_id": outline_row.id,
                    "title": outline_row.title,
                    "course_query": outline_row.course_query,
                    "generated_at": outline_row.created_at.isoformat() if outline_row.created_at else None,
                }
            except (ValueError, TypeError):
                outline = None

        cohort = cohort_records if cohort_records is not None else records
        resources = await self.course_resources(tenant_id, course_id)
        q_count = self.analysis.check_quality(records)
        report = self.analysis.individual_summary(records, student, q_count, course_name)

        needs = report["needs_consolidation"]
        fair = report["fair_areas"]
        insufficient = report["insufficient_evidence"]
        overall = report["overall"]
        accuracy = overall.get("accuracy")
        attempts = overall.get("attempts") or 0

        # 目标知识点：先补「需巩固」，有富余再取「基本掌握」里正确率最低的
        targets = [dict(x, status="needs_work") for x in needs]
        if len(targets) < 2 and fair:
            targets.append(dict(sorted(fair, key=lambda x: x.get("accuracy") or 0)[0], status="fair"))
        if focus:
            for x in report["knowledge_points"]:
                if _norm(focus) in _norm(x["knowledge_point"]) and all(
                    t["knowledge_point"] != x["knowledge_point"] for t in targets
                ):
                    targets.insert(0, dict(x, status=x.get("status")))

        items: List[Dict[str, Any]] = []
        order = 1
        for row in targets[:4]:
            match = self._match_outline(row["knowledge_point"], outline)
            stats = await self._course_weak_stats(cohort, row["knowledge_point"])
            items.append(
                self._build_item(order, row, match, outline, resources, stats, focus)
            )
            order += 1

        # 先后安排：大纲单元顺序 + 先修关系（拓扑）
        items = self._order_items(items, outline)

        # 证据不足 → 补充观察建议，而不是硬给补强方案
        observation_items: List[Dict[str, Any]] = []
        for row in insufficient[:4]:
            observation_items.append(
                {
                    "knowledge_point": row["knowledge_point"],
                    "evidence": row["evidence_text"],
                    "action": f"先做 3 次「{row['knowledge_point']}」诊断性练习（每次 5 题，覆盖概念/过程/应用各 1–2 题）",
                    "decision_rule": "3 次累计正确率 < 60% → 转入补强清单；≥ 60% → 只做巩固练习，不占用主课时",
                    "reason": "该知识点当前作答次数少于判断门槛（3 次），按规则不下「掌握/未掌握」结论，先补观察数据",
                }
            )

        if not records and outline:
            for unit in (outline.get("units") or [])[:2]:
                contents = unit.get("contents") or []
                if not contents:
                    continue
                topics = "、".join(c.get("topic", "") for c in contents[:3])
                observation_items.append(
                    {
                        "knowledge_point": unit.get("name") or topics,
                        "evidence": "该生在本课程暂无作答记录，无法判断掌握情况",
                        "action": f"先做「{topics}」的基线诊断练习：10 题，概念 4 题 + 过程 4 题 + 应用 2 题",
                        "decision_rule": "正确率 < 60% → 该单元进入补强清单；60%~80% → 只做巩固练习；≥ 80% → 跳过，把时间留给下一个单元",
                        "reason": "信息不足时不预设结论，用一次基线诊断把「不知道」变成可判断的数据",
                    }
                )

        student_insufficient = attempts < 3
        if student_insufficient:
            goal_overview = (
                f"当前可判断作答仅 {attempts} 条，证据不足以给出「补什么」的结论。"
                "本方案以「补充观察 + 基础诊断」为主：先补齐 3 次以上针对性练习，再据结果调整补强内容。"
            )
        elif items:
            kps = "、".join(i["knowledge_point"] for i in items)
            goal_overview = (
                f"用 {duration_days} 天把 {kps} 从「{items[0]['status_label']}」提到「变式题正确率 ≥80%」，"
                "每次练习后按验收标准决定是否进入下一步。"
            )
        elif observation_items:
            goal_overview = (
                "现有记录还不足以判断「哪里薄弱」（每个知识点的作答次数都低于 3 次），"
                f"先用 {duration_days} 天补齐观察数据，再据结果决定补强内容；不预先判定为「没学会」。"
            )
        else:
            goal_overview = "本课程暂无需巩固的知识点，建议以保持性练习和拓展任务为主。"

        schedule = self._schedule(items, duration_days)

        # 教师调整建议
        teacher_notes: List[str] = []
        if items:
            teacher_notes.append(
                "题量可调：诊断题是「探底」，正确率已低于 40% 的学生可只做 3 题就进入讲解；变式题是达标关键，不建议减"
            )
            teacher_notes.append(
                "时间可调：每个条目标了预计分钟数，若课堂已讲过对应内容，可整体压缩 30%，把时间留给变式题讲评"
            )
        common = [i for i in items if "班级共性" in i["reason"]]
        if common:
            teacher_notes.append(
                f"课堂优先：{'、'.join(i['knowledge_point'] for i in common)} 属班级共性问题，建议先用 10 分钟统一讲评，再发个性化练习"
            )
        if observation_items:
            teacher_notes.append(
                "证据不足项不要直接判「没学会」：先按补充观察建议收集 3 次练习数据，再决定是否进入补强"
            )
        if not items and observation_items:
            teacher_notes.append(
                "本次没有可靠证据支撑「补什么」，方案以补充观察为主：按建议做诊断练习后重新生成一次，建议会自动变成补强型方案"
            )
        if not outline_meta.get("available"):
            teacher_notes.append(
                "本次未找到该课程的梳理大纲，学习要求按通用层次生成；建议先做一次「课程梳理」，建议会更贴合教材"
            )

        data_notes = list(report.get("data_notes") or [])
        if overall.get("records_valid"):
            data_notes.append(
                f"本方案基于 {overall['records_valid']} 条有效记录（其中 {attempts} 条可判断对错）与"
                + (" 1 份课程大纲" if outline_meta.get("available") else "通用学习要求")
                + f"生成；阈值：单知识点 ≥3 次才判断，正确率 <60% 记需巩固、≥80% 记掌握良好。"
            )

        materials_index: List[Dict[str, Any]] = []
        seen_titles = set()
        for item in items:
            for m in item["materials"]:
                key = (m["kind"], m["title"])
                if key in seen_titles:
                    continue
                seen_titles.add(key)
                materials_index.append({**m, "for": item["knowledge_point"], "order": item["order"]})

        return {
            "student": student,
            "course": course,
            "duration_days": duration_days,
            "focus": focus,
            "engine": "rule+outline" if outline_meta.get("available") else "rule",
            "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
            "summary": {
                "accuracy": accuracy,
                "attempts": attempts,
                "records_valid": overall.get("records_valid"),
                "weak_count": len(needs),
                "fair_count": len(fair),
                "insufficient_count": len(insufficient),
                "student_evidence_sufficient": not student_insufficient,
            },
            "goal_overview": goal_overview,
            "items": items,
            "observation_items": observation_items,
            "schedule": schedule,
            "teacher_notes": teacher_notes,
            "data_notes": data_notes,
            "materials_index": materials_index,
            "outline": outline_meta,
            "resources_checked": len(resources),
            "thresholds": report.get("thresholds"),
        }

    # ------------------------------------------------------------------
    # 排序与排期
    # ------------------------------------------------------------------
    def _order_items(
        self, items: List[Dict[str, Any]], outline: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """先按大纲单元顺序，再用 connections 的先修关系做一次稳定调整"""
        if not items:
            return items
        items.sort(
            key=lambda x: (
                x["outline"].get("unit_index") if x["outline"].get("unit_index") is not None else 99,
                x["outline"].get("content_index") or 0,
                x["order"],
            )
        )

        # 先修边：from_topic 属于 A 的内容、to_topic 属于 B 的内容 → A 先于 B
        topic_owner: Dict[str, str] = {}
        for it in items:
            for topic in it["outline"].get("topics", []) or []:
                topic_owner[_norm(topic)] = it["knowledge_point"]
        edges: List[Tuple[str, str]] = []
        for conn in (outline or {}).get("connections") or []:
            a = topic_owner.get(_norm(conn.get("from_topic", "")))
            b = topic_owner.get(_norm(conn.get("to_topic", "")))
            if a and b and a != b:
                edges.append((a, b))

        # 简单稳定拓扑：有先修关系的排前面，其余保持原顺序
        if edges:
            indeg = {it["knowledge_point"]: 0 for it in items}
            for a, b in edges:
                indeg[b] = indeg.get(b, 0) + 1
            ordered: List[Dict[str, Any]] = []
            remaining = list(items)  # 保持单元顺序，只在有先修关系时调整
            guard = 0
            while remaining and guard < 20:
                guard += 1
                progressed = False
                for it in list(remaining):
                    if indeg.get(it["knowledge_point"], 0) == 0:
                        ordered.append(it)
                        remaining.remove(it)
                        for a, b in edges:
                            if a == it["knowledge_point"]:
                                indeg[b] = max(0, indeg.get(b, 0) - 1)
                        progressed = True
                        break
                if not progressed:
                    ordered.extend(remaining)
                    break
            items = ordered

        for it in items:
            pre = it.get("prerequisites") or []
            if not pre:
                continue
            p0 = pre[0]
            owner = topic_owner.get(_norm(p0.get("from_topic", "")))
            if owner and owner != it["knowledge_point"]:
                it["order_reason"] = (
                    f"先学「{owner}」再练「{it['knowledge_point']}」：{p0.get('description', '')}"
                )
            else:
                it["order_reason"] = (
                    f"前置：「{it['knowledge_point']}」需要「{p0.get('from_topic')}」打底"
                    f"（{p0.get('description', '')}）；若该前置也不牢，先花 20 分钟补它再回到本步"
                )

        for i, it in enumerate(items, start=1):
            it["order"] = i
        return items

    def _schedule(self, items: List[Dict[str, Any]], duration_days: int) -> List[Dict[str, Any]]:
        """把条目分配到天：每天 60 分钟上限，最后留一天复盘"""
        if not items:
            return []
        days: List[Dict[str, Any]] = []
        day, used = 1, 0
        review_day = max(duration_days, 1)
        for it in items:
            m = it["estimated_minutes"]
            if used and used + m > 60 and day < review_day:
                day += 1
                used = 0
            days.append(
                {
                    "day": day,
                    "item_orders": [it["order"]],
                    "knowledge_points": [it["knowledge_point"]],
                    "minutes": m,
                }
            )
            used += m
        merged: List[Dict[str, Any]] = []
        for d in days:
            if merged and merged[-1]["day"] == d["day"]:
                merged[-1]["item_orders"].extend(d["item_orders"])
                merged[-1]["knowledge_points"].extend(d["knowledge_points"])
                merged[-1]["minutes"] += d["minutes"]
            else:
                merged.append(d)
        for d in merged:
            d["note"] = "先做诊断题，再按验收标准决定是否继续" if d["minutes"] <= 60 else "内容较多，可拆成两次 30 分钟"
        # 步骤没排满的中间天数标成缓冲，避免出现「第 4 天 → 第 7 天」的跳号
        last_day = merged[-1]["day"] if merged else 0
        for d in range(last_day + 1, review_day):
            merged.append(
                {
                    "day": d,
                    "item_orders": [],
                    "knowledge_points": ["缓冲"],
                    "minutes": 30,
                    "note": "缓冲：补做未达标条目，或按需插入一次课堂讲评",
                }
            )

        if review_day > (merged[-1]["day"] if merged else 0):
            merged.append(
                {
                    "day": review_day,
                    "item_orders": [it["order"] for it in items],
                    "knowledge_points": ["复盘与复测"],
                    "minutes": 25,
                    "note": "重做各知识点的变式题各 3 题，正确率 ≥80% 视为达成；未达标的条目顺延",
                }
            )
        return merged

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------
    def render_markdown(self, plan: Dict[str, Any]) -> str:
        s = plan["student"]
        c = plan["course"]
        lines: List[str] = []
        lines.append(f"# {s.get('name', '学生')} · {c.get('name', '课程')} 个性化学习建议")
        lines.append("")
        lines.append(
            f"> 生成时间：{plan['generated_at']}　周期：{plan['duration_days']} 天　"
            f"引擎：{plan['engine']}　依据："
            + (f"大纲「{plan['outline'].get('title')}」" if plan["outline"].get("available") else "通用学习要求")
        )
        lines.append("")
        lines.append("## 一、本次目标")
        lines.append(plan["goal_overview"])
        lines.append("")

        summary = plan["summary"]
        lines.append("## 二、学情依据")
        lines.append(
            f"- 可判断作答 {summary['attempts']} 条，整体正确率 "
            f"{(summary['accuracy'] * 100):.1f}%" if summary["accuracy"] is not None else "- 暂无可判断作答记录"
        )
        lines.append(
            f"- 需巩固 {summary['weak_count']} 项 / 基本掌握 {summary['fair_count']} 项 / 证据不足 {summary['insufficient_count']} 项"
        )
        for note in plan["data_notes"]:
            lines.append(f"- {note}")
        lines.append("")

        lines.append("## 三、建议内容与先后安排")
        for it in plan["items"]:
            lines.append(f"### 第 {it['order']} 步：{it['knowledge_point']}（{it['status_label']}）")
            lines.append(f"- **问题**：{it['problem']}")
            lines.append(f"- **目标**：{it['goal']}（认知层次：{it['goal_level']}）")
            lines.append(f"- **选择理由**：{it['reason']}")
            lines.append("- **学习内容**：" + "；".join(it["content"]))
            lines.append("- **练习安排**：")
            for p in it["practices"]:
                lines.append(f"  - {p['stage']}：{p['count']} 题，{p['desc']}；达标线：{p['pass_line']}")
            lines.append(f"- **活动建议**：{it['activity']}")
            lines.append("- **对应材料**：")
            for m in it["materials"]:
                extra = f"（{m.get('rule')}）" if m.get("rule") else ""
                lines.append(f"  - [{m['kind']}] {m['title']}{extra}")
            lines.append(f"- **验收标准**：{it['acceptance']}")
            lines.append(f"- **先后说明**：{it['order_reason']}（预计 {it['estimated_minutes']} 分钟）")
            lines.append(f"- **教师调整**：{it['teacher_tip']}")
            lines.append("")

        if plan["observation_items"]:
            lines.append("## 四、信息不足：补充观察与练习建议")
            for o in plan["observation_items"]:
                lines.append(f"- **{o['knowledge_point']}**：{o['evidence']}")
                lines.append(f"  - 建议：{o['action']}")
                lines.append(f"  - 判断规则：{o['decision_rule']}")
            lines.append("")

        if plan["schedule"]:
            lines.append("## 五、时间安排")
            for d in plan["schedule"]:
                if d["item_orders"]:
                    head = f"第 {'、'.join(str(x) for x in d['item_orders'])} 步"
                else:
                    head = "缓冲（无固定步骤）"
                lines.append(f"- 第 {d['day']} 天：{head}，{d['minutes']} 分钟 —— {d['note']}")
            lines.append("")

        if plan["teacher_notes"]:
            lines.append("## 六、给教师的调整建议")
            for n in plan["teacher_notes"]:
                lines.append(f"- {n}")
            lines.append("")

        lines.append("## 七、材料清单（可追溯）")
        for m in plan["materials_index"]:
            src = f"｜来源：{m.get('source')}"
            rule = f"｜规则：{m.get('rule')}" if m.get("rule") else ""
            lines.append(f"- [{m['kind']}] {m['title']}（用于第 {m['order']} 步 {m['for']}）{src}{rule}")
        lines.append("")
        return "\n".join(lines)
