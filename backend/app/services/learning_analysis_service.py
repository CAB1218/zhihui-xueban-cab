"""
AI4EDU 学情分析服务
任务2（理解学生-学生学习情况分析）

三段式流程：
    1. 质量检查：识别缺失 / 异常 / 重复，给出每类的处理方式与处理前后条数
    2. 个体摘要：单个学生的表现、需巩固内容、证据记录、证据不足说明
    3. 群体摘要：班级共性薄弱点、个体差异、统计依据

设计原则（对应赛题要求）：
    · 每条结论必须能追到记录 ID 或统计量，不写没有依据的判断
    · 样本量不足时标注「证据不足，尚不能判断」，绝不写成「未掌握」
    · 分析维度以实际数据为准，缺失率过高的维度直接声明不纳入分析
"""
from __future__ import annotations

import copy
import json
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.learning_record import LearningRecord
from app.models.user import User

logger = logging.getLogger(__name__)

# ---- 判定阈值（在成果中会明示，避免"黑箱"） ----
MIN_ATTEMPTS_FOR_JUDGEMENT = 3   # 少于 3 次作答不下掌握/未掌握结论
ACC_GOOD = 0.80                  # ≥80% 记为掌握良好
ACC_WEAK = 0.60                  # <60% 记为需巩固
COMMON_WEAK_RATIO = 0.50         # ≥50% 学生薄弱即视为共性问题
DURATION_MAX_REASONABLE = 6 * 3600  # 超过 6 小时视为异常耗时

STATUS_META = {
    "good": ("掌握良好", "success"),
    "fair": ("基本掌握", "primary"),
    "needs_work": ("需巩固", "warning"),
    "insufficient": ("证据不足，尚不能判断", "info"),
}


# ---------------------------------------------------------------------------
# 内部数据结构
# ---------------------------------------------------------------------------
@dataclass
class RecordView:
    """记录的只读视图，避免直接改动 ORM 对象"""

    id: int
    student_id: int
    course_id: Optional[int]
    knowledge_point: Optional[str]
    record_type: str
    source_ref: Optional[str]
    question_count: Optional[int]
    is_correct: Optional[bool]
    score: Optional[float]
    max_score: Optional[float]
    duration_seconds: Optional[int]
    recorded_at: datetime
    flags: List[str] = field(default_factory=list)

    @property
    def dedup_key(self) -> tuple:
        """完全重复判定键：业务字段全同即视为同一份记录被重复上报"""
        return (
            self.student_id,
            self.course_id,
            self.knowledge_point,
            self.record_type,
            self.score,
            self.max_score,
            self.duration_seconds,
            self.recorded_at,
        )

    @property
    def near_dup_key(self) -> tuple:
        """近似重复：同一学生、同一知识点、同一分钟内的多次提交"""
        return (
            self.student_id,
            self.knowledge_point,
            self.recorded_at.strftime("%Y-%m-%d %H:%M"),
        )

    @property
    def judgeable(self) -> bool:
        """能否判断对错：有 is_correct，或能由 score/max_score 推断"""
        if self.is_correct is not None:
            return True
        return self.score is not None and self.max_score not in (None, 0)

    @property
    def correct(self) -> Optional[bool]:
        if self.is_correct is not None:
            return self.is_correct
        if self.score is not None and self.max_score:
            return self.score / self.max_score >= 0.6
        return None


@dataclass
class QualityResult:
    raw_count: int
    valid: List[RecordView]
    issues: List[Dict[str, Any]]
    steps: List[Dict[str, Any]]
    notes: List[str]
    counts: Dict[str, int]

    @property
    def valid_count(self) -> int:
        return len(self.valid)


_CN_DIGITS = "一二三四五六七八九十"


class _SectionNumber:
    """报告章节自动编号，避免某些小节为空时出现「一二六」这样的跳号"""

    def __init__(self, start: int = 1) -> None:
        self.n = start

    def title(self, text: str) -> str:
        num = _CN_DIGITS[self.n - 1] if self.n <= len(_CN_DIGITS) else str(self.n)
        self.n += 1
        return f"## {num}、{text}"


def _to_view(r: LearningRecord) -> RecordView:
    return RecordView(
        id=r.id,
        student_id=r.student_id,
        course_id=r.course_id,
        knowledge_point=(r.knowledge_point or "").strip() or None,
        record_type=r.record_type,
        source_ref=r.source_ref,
        question_count=r.question_count,
        is_correct=r.is_correct,
        score=r.score,
        max_score=r.max_score,
        duration_seconds=r.duration_seconds,
        recorded_at=r.recorded_at,
    )


class LearningAnalysisService:
    """学情分析服务"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 数据读取
    # ------------------------------------------------------------------
    async def load_records(
        self, tenant_id: int, course_id: Optional[int] = None
    ) -> List[RecordView]:
        stmt = select(LearningRecord).where(LearningRecord.tenant_id == tenant_id)
        if course_id:
            stmt = stmt.where(LearningRecord.course_id == course_id)
        stmt = stmt.order_by(LearningRecord.recorded_at)
        rows = (await self.db.execute(stmt)).scalars().all()
        return [_to_view(r) for r in rows]

    async def list_students(self, tenant_id: int) -> List[Dict[str, Any]]:
        """有学情记录的学生列表（含记录数，便于前端排序展示）"""
        records = await self.load_records(tenant_id)
        by_student: Dict[int, List[RecordView]] = {}
        for r in records:
            by_student.setdefault(r.student_id, []).append(r)

        users = (
            await self.db.execute(select(User).where(User.id.in_(list(by_student.keys()))))
        ).scalars().all()
        umap = {u.id: u for u in users}

        out = []
        for sid, recs in by_student.items():
            u = umap.get(sid)
            judgeable = [r for r in recs if r.judgeable]
            acc = (
                sum(1 for r in judgeable if r.correct) / len(judgeable) if judgeable else None
            )
            out.append(
                {
                    "student_id": sid,
                    "name": u.nickname if u else f"学生{sid}",
                    "grade": u.grade if u else None,
                    "major": u.major if u else None,
                    "record_count": len(recs),
                    "judgeable_count": len(judgeable),
                    "accuracy": round(acc, 4) if acc is not None else None,
                    "courses": sorted({r.course_id for r in recs if r.course_id}),
                }
            )
        out.sort(key=lambda x: (-(x["record_count"] or 0), x["name"]))
        return out

    # ------------------------------------------------------------------
    # 一、数据质量检查
    # ------------------------------------------------------------------
    def check_quality(self, records: Sequence[RecordView]) -> QualityResult:
        raw = list(records)
        raw_count = len(raw)
        issues: List[Dict[str, Any]] = []
        steps: List[Dict[str, Any]] = []
        notes: List[str] = []

        # 清洗会修改字段（截断分数、置空耗时），用副本避免污染调用方数据
        working = [copy.copy(r) for r in raw]

        # ---------- 步骤 1：完全重复 ----------
        before = len(working)
        seen: Dict[tuple, RecordView] = {}
        exact_dups: List[RecordView] = []
        kept: List[RecordView] = []
        for r in working:
            key = r.dedup_key
            if key in seen:
                exact_dups.append(r)
            else:
                seen[key] = r
                kept.append(r)
        working = kept
        steps.append({"step": "完全重复去重", "before": before, "after": len(working),
                      "removed": before - len(working)})
        if exact_dups:
            issues.append(
                {
                    "type": "duplicate",
                    "code": "exact_duplicate",
                    "title": "完全重复记录",
                    "count": len(exact_dups),
                    "record_ids": [r.id for r in exact_dups][:20],
                    "detail": (
                        "同一学生在同一时刻、同一知识点上产生了业务字段完全相同的多条记录，"
                        "判断为重复上报（可能是提交接口重试或客户端重复提交）。"
                    ),
                    "handling": "保留 ID 最小的一条，其余剔除；重复条目不重复计入作答次数",
                    "handling_type": "剔除",
                }
            )

        # ---------- 步骤 2：近似重复 ----------
        before = len(working)
        near_seen: Dict[tuple, List[RecordView]] = {}
        for r in working:
            near_seen.setdefault(r.near_dup_key, []).append(r)

        near_dups: List[RecordView] = []
        kept = []
        for key, group in near_seen.items():
            if len(group) == 1:
                kept.append(group[0])
                continue
            # 同一分钟内的多次提交：优先保留得分更高的一条（视作重考/订正后的结果）
            group_sorted = sorted(
                group,
                key=lambda x: (
                    (x.score if x.score is not None else -1),
                    x.id,
                ),
                reverse=True,
            )
            kept.append(group_sorted[0])
            near_dups.extend(group_sorted[1:])
        working = kept
        steps.append({"step": "同人同知识点同时段重复提交合并", "before": before,
                      "after": len(working), "removed": before - len(working)})
        if near_dups:
            issues.append(
                {
                    "type": "duplicate",
                    "code": "near_duplicate",
                    "title": "同人同知识点同时段的重复提交",
                    "count": len(near_dups),
                    "record_ids": [r.id for r in near_dups][:20],
                    "detail": (
                        "同一学生在一分钟内对同一知识点提交了多次且得分不同，"
                        "符合「订正后重新提交」或「重复点击提交」的特征，无法仅凭数据区分。"
                    ),
                    "handling": "保留得分最高的一条作为最终结果，其余合并；不累加作答次数，避免高估练习量",
                    "handling_type": "合并",
                }
            )

        # ---------- 步骤 3：异常 — 未来时间 ----------
        now = datetime.now()
        future = [r for r in working if r.recorded_at > now]
        if future:
            working = [r for r in working if r.recorded_at <= now]
            issues.append(
                {
                    "type": "abnormal",
                    "code": "future_timestamp",
                    "title": "记录时间在未来",
                    "count": len(future),
                    "record_ids": [r.id for r in future][:20],
                    "detail": (
                        "记录时间晚于当前系统时间，属于设备时钟错误或导入时的时区错位，"
                        "无法确定真实发生时间。"
                    ),
                    "handling": "整条剔除（不纳入时间序列与趋势分析），原始数据保留可溯源",
                    "handling_type": "剔除",
                }
            )
        steps.append({"step": "剔除未来时间记录", "before": len(working) + len(future),
                      "after": len(working), "removed": len(future)})

        # ---------- 步骤 4：异常 — 分数超满分（字段级修正） ----------
        over = [r for r in working if r.score is not None and r.max_score and r.score > r.max_score]
        for r in over:
            r.flags.append("score_clamped")
            r.score = r.max_score
        if over:
            issues.append(
                {
                    "type": "abnormal",
                    "code": "score_over_max",
                    "title": "得分超过满分",
                    "count": len(over),
                    "record_ids": [r.id for r in over][:20],
                    "detail": (
                        "得分大于该次作答的满分，可能是加分题未同步满分值，或录入时的小数点错位。"
                    ),
                    "handling": "按满分截断（clamp）后保留，不整条剔除；原始分数保留在原始记录中可追溯",
                    "handling_type": "修正",
                }
            )

        # ---------- 步骤 5：异常 — 耗时不合理（字段级置空） ----------
        bad_dur = [
            r for r in working
            if r.duration_seconds is not None
            and (r.duration_seconds < 0 or r.duration_seconds > DURATION_MAX_REASONABLE)
        ]
        for r in bad_dur:
            r.flags.append("duration_invalid")
            r.duration_seconds = None
        if bad_dur:
            issues.append(
                {
                    "type": "abnormal",
                    "code": "duration_invalid",
                    "title": "作答耗时异常（负数或超过 6 小时）",
                    "count": len(bad_dur),
                    "record_ids": [r.id for r in bad_dur][:20],
                    "detail": (
                        "耗时出现负值，或长到明显不是连续作答（如 86400 秒 = 24 小时），"
                        "多为页面长时间未关闭、后台挂起导致的计时错误。"
                    ),
                    "handling": "耗时字段置空，保留该记录的得分与对错用于正确率分析；不参与时长维度统计",
                    "handling_type": "修正",
                }
            )

        # ---------- 步骤 6：缺失 — 结果完全不可判定 ----------
        before = len(working)
        unjudgeable = [r for r in working if not r.judgeable]
        working = [r for r in working if r.judgeable]
        steps.append({"step": "剔除结果完全缺失的记录", "before": before,
                      "after": len(working), "removed": before - len(working)})
        if unjudgeable:
            issues.append(
                {
                    "type": "missing",
                    "code": "result_missing",
                    "title": "得分与对错同时缺失",
                    "count": len(unjudgeable),
                    "record_ids": [r.id for r in unjudgeable][:20],
                    "detail": (
                        "该记录的得分和对错标记都为空，无法判断这次作答的结果，"
                        "属于采集链路不完整，不能据此推断学生掌握情况。"
                    ),
                    "handling": "从有效分析集剔除，不计入任何正确率分母；单独列出供教务核对补录",
                    "handling_type": "剔除",
                }
            )

        # ---------- 缺失：分值缺失但有对错 ----------
        score_missing = [r for r in working if r.score is None and r.is_correct is not None]
        if score_missing:
            issues.append(
                {
                    "type": "missing",
                    "code": "score_missing",
                    "title": "分值为空但保留对错标记",
                    "count": len(score_missing),
                    "record_ids": [r.id for r in score_missing][:20],
                    "detail": (
                        "分数没有回传，但该次作答的对错标记完整，仍可判断这一题是否答对。"
                    ),
                    "handling": "保留：计入作答次数与正确率，不参与得分率计算",
                    "handling_type": "保留",
                }
            )

        # ---------- 缺失：知识点缺失 ----------
        kp_missing = [r for r in working if not r.knowledge_point]
        if kp_missing:
            issues.append(
                {
                    "type": "missing",
                    "code": "kp_missing",
                    "title": "知识点为空",
                    "count": len(kp_missing),
                    "record_ids": [r.id for r in kp_missing][:20],
                    "detail": (
                        "记录没有归到具体知识点，可能是题目未绑定知识图谱节点。"
                        "这类记录只能进入整体统计，无法参与知识点维度分析。"
                    ),
                    "handling": "保留在总体统计中；知识点维度分析时排除，并在报告中说明该部分未计入",
                    "handling_type": "保留（降级使用）",
                }
            )

        # ---------- 缺失：耗时缺失 ----------
        dur_missing = [r for r in working if r.duration_seconds is None]
        if dur_missing:
            issues.append(
                {
                    "type": "missing",
                    "code": "duration_missing",
                    "title": "作答耗时为空",
                    "count": len(dur_missing),
                    "record_ids": [r.id for r in dur_missing][:20],
                    "detail": "未能采集到作答耗时，不影响正确率判断。",
                    "handling": "时长为空的记录不进入时长统计，正确率分析照常使用",
                    "handling_type": "保留（降级使用）",
                }
            )

        # ---------- 汇总 ----------
        counts = {
            "missing": sum(i["count"] for i in issues if i["type"] == "missing"),
            "abnormal": sum(i["count"] for i in issues if i["type"] == "abnormal"),
            "duplicate": sum(i["count"] for i in issues if i["type"] == "duplicate"),
        }

        notes.append(
            f"原始记录 {raw_count} 条，经去重与清洗后得到有效记录 {len(working)} 条，"
            f"剔除 {raw_count - len(working)} 条。"
        )
        notes.append(
            "一条记录可能同时命中多类问题（例如既重复又分值异常），处理按「去重 → 异常 → 缺失」"
            "的顺序执行，每步的条数变化在上表的 before/after 中列出，因此各类问题条数之和可能"
            "大于总剔除数。"
        )
        notes.append(
            "剔除只影响分析口径，原始记录一律保留在库中，可随时回溯核对。"
        )

        return QualityResult(
            raw_count=raw_count,
            valid=working,
            issues=issues,
            steps=steps,
            notes=notes,
            counts=counts,
        )

    # ------------------------------------------------------------------
    # 二、个体摘要
    # ------------------------------------------------------------------
    def individual_summary(
        self,
        records: Sequence[RecordView],
        student: Dict[str, Any],
        quality: Optional[QualityResult] = None,
        course_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        q = quality or self.check_quality(records)
        valid = q.valid
        judgeable = [r for r in valid if r.judgeable]

        attempts = len(judgeable)
        correct_n = sum(1 for r in judgeable if r.correct)
        accuracy = round(correct_n / attempts, 4) if attempts else None

        # 按知识点聚合
        by_kp: Dict[str, List[RecordView]] = {}
        for r in judgeable:
            if not r.knowledge_point:
                continue
            by_kp.setdefault(r.knowledge_point, []).append(r)

        kp_rows = []
        for kp, recs in by_kp.items():
            n = len(recs)
            c = sum(1 for r in recs if r.correct)
            acc = c / n if n else 0.0
            if n < MIN_ATTEMPTS_FOR_JUDGEMENT:
                status = "insufficient"
            elif acc >= ACC_GOOD:
                status = "good"
            elif acc < ACC_WEAK:
                status = "needs_work"
            else:
                # 60%~80% 之间不称"掌握良好"，也不到"需巩固"，单独一档避免夸大
                status = "fair"
            kp_rows.append(
                {
                    "knowledge_point": kp,
                    "attempts": n,
                    "correct_count": c,
                    "accuracy": round(acc, 4),
                    "status": status,
                    "status_label": STATUS_META[status][0],
                    "evidence_record_ids": [r.id for r in recs][:12],
                    "evidence_text": f"{n} 次作答中 {c} 次正确，正确率 {acc * 100:.1f}%",
                }
            )
        kp_rows.sort(key=lambda x: (x["status"] != "needs_work", x["accuracy"]))

        needs = [r for r in kp_rows if r["status"] == "needs_work"]
        fair = [r for r in kp_rows if r["status"] == "fair"]
        good = [r for r in kp_rows if r["status"] == "good"]
        insufficient = [r for r in kp_rows if r["status"] == "insufficient"]

        # 参与情况
        type_count: Dict[str, int] = {}
        for r in valid:
            type_count[r.record_type] = type_count.get(r.record_type, 0) + 1
        dates = sorted({r.recorded_at.date() for r in valid})
        span = (dates[-1] - dates[0]).days + 1 if len(dates) >= 2 else (1 if dates else 0)

        # 时长维度可用性
        dur_ok = [r for r in valid if r.duration_seconds is not None]
        dur_ratio = len(dur_ok) / len(valid) if valid else 0.0
        avg_dur = (
            round(statistics.mean(r.duration_seconds for r in dur_ok) / 60, 1) if dur_ok else None
        )

        data_notes = []
        data_notes.append(
            f"本课程有效记录 {len(valid)} 条，其中 {attempts} 条可判断对错；"
            f"{len(valid) - attempts} 条仅有分值或信息不完整，已从正确率分母中排除。"
        )
        dropped = q.raw_count - len(valid)
        if dropped:
            data_notes.append(f"清洗阶段剔除了 {dropped} 条重复或无法判定的记录，原始数据仍在库中可查。")
        if insufficient:
            names = "、".join(x["knowledge_point"] for x in insufficient[:5])
            data_notes.append(
                f"{names} 等 {len(insufficient)} 个知识点的作答次数少于 "
                f"{MIN_ATTEMPTS_FOR_JUDGEMENT} 次，**样本不足以判断掌握情况**，"
                "已在表中标注为「证据不足」，这不等于未掌握。"
            )
        if dur_ratio < 0.5:
            data_notes.append(
                f"作答耗时字段可用率仅 {dur_ratio * 100:.0f}%，本次不将学习时长作为分析维度。"
            )

        return {
            "student": student,
            "course_name": course_name,
            "overall": {
                "records_total": q.raw_count,
                "records_valid": len(valid),
                "attempts": attempts,
                "correct_count": correct_n,
                "accuracy": accuracy,
                "accuracy_basis": f"基于 {attempts} 条可判断对错的记录计算",
                "knowledge_point_count": len(kp_rows),
                "practice_days": span,
                "record_type_distribution": type_count,
                "avg_duration_minutes": avg_dur,
            },
            "knowledge_points": kp_rows,
            "needs_consolidation": needs,
            "fair_areas": fair,
            "strengths": good,
            "insufficient_evidence": insufficient,
            "data_notes": data_notes,
            "thresholds": {
                "min_attempts": MIN_ATTEMPTS_FOR_JUDGEMENT,
                "acc_good": ACC_GOOD,
                "acc_weak": ACC_WEAK,
            },
        }

    # ------------------------------------------------------------------
    # 三、群体摘要
    # ------------------------------------------------------------------
    def group_summary(
        self,
        records: Sequence[RecordView],
        course: Dict[str, Any],
        students: Optional[Dict[int, Dict[str, Any]]] = None,
        quality: Optional[QualityResult] = None,
    ) -> Dict[str, Any]:
        q = quality or self.check_quality(records)
        valid = q.valid
        judgeable = [r for r in valid if r.judgeable]
        students = students or {}

        # 按学生聚合
        by_student: Dict[int, List[RecordView]] = {}
        for r in judgeable:
            by_student.setdefault(r.student_id, []).append(r)

        student_stats = []
        for sid, recs in by_student.items():
            n = len(recs)
            c = sum(1 for r in recs if r.correct)
            info = students.get(sid, {})
            # 该学生在多少个知识点上达到了最低判定样本量——只有这些点上的结论才站得住
            per_kp_n: Dict[str, int] = {}
            for r in recs:
                if r.knowledge_point:
                    per_kp_n[r.knowledge_point] = per_kp_n.get(r.knowledge_point, 0) + 1
            reliable_kp = sum(1 for v in per_kp_n.values() if v >= MIN_ATTEMPTS_FOR_JUDGEMENT)
            student_stats.append(
                {
                    "student_id": sid,
                    "name": info.get("name", f"学生{sid}"),
                    "attempts": n,
                    "correct_count": c,
                    "accuracy": round(c / n, 4) if n else None,
                    "knowledge_points_practiced": len(per_kp_n),
                    "reliable_kp_count": reliable_kp,
                }
            )
        judged_students = [s for s in student_stats if s["accuracy"] is not None]
        judged_students.sort(key=lambda x: -(x["accuracy"] or 0))

        # 横向比较只看「有足够样本支撑至少一个结论」的学生：
        # 总量够但每个知识点只做过一两次的学生，正确率是偶然波动，排名会得出错误结论
        reliable_students = [s for s in judged_students if s["reliable_kp_count"] >= 1]
        sparse_students = [s for s in judged_students if s["reliable_kp_count"] == 0]

        # 班级整体
        total_attempts = sum(s["attempts"] for s in judged_students)
        total_correct = sum(s["correct_count"] for s in judged_students)
        class_acc = round(total_correct / total_attempts, 4) if total_attempts else None

        # 按知识点聚合 + 共性薄弱点
        kp_students: Dict[str, List[Dict[str, Any]]] = {}
        for sid, recs in by_student.items():
            per_kp: Dict[str, List[RecordView]] = {}
            for r in recs:
                if r.knowledge_point:
                    per_kp.setdefault(r.knowledge_point, []).append(r)
            for kp, rs in per_kp.items():
                n = len(rs)
                c = sum(1 for x in rs if x.correct)
                kp_students.setdefault(kp, []).append(
                    {
                        "student_id": sid,
                        "name": students.get(sid, {}).get("name", f"学生{sid}"),
                        "attempts": n,
                        "correct_count": c,
                        "accuracy": round(c / n, 4),
                        "judgeable": n >= MIN_ATTEMPTS_FOR_JUDGEMENT,
                    }
                )

        kp_summary = []
        common_weak = []
        for kp, rows in kp_students.items():
            n_students = len(rows)
            total_n = sum(r["attempts"] for r in rows)
            total_c = sum(r["correct_count"] for r in rows)
            acc = round(total_c / total_n, 4) if total_n else 0.0
            weak = [r for r in rows if r["judgeable"] and r["accuracy"] < ACC_WEAK]
            weak_ratio = round(len(weak) / n_students, 4) if n_students else 0.0
            item = {
                "knowledge_point": kp,
                "students_practiced": n_students,
                "attempts": total_n,
                "accuracy": acc,
                "weak_students": len(weak),
                "weak_ratio": weak_ratio,
                "is_common_weak": len(weak) >= 2 and weak_ratio >= COMMON_WEAK_RATIO,
            }
            kp_summary.append(item)
            if item["is_common_weak"]:
                item = dict(item)
                item["weak_student_names"] = [w["name"] for w in weak][:8]
                item["evidence_text"] = (
                    f"{n_students} 名有作答记录的学生中，{len(weak)} 名在该知识点上正确率低于 "
                    f"{ACC_WEAK * 100:.0f}%，整体正确率 {acc * 100:.1f}%"
                )
                common_weak.append(item)

        kp_summary.sort(key=lambda x: x["accuracy"])
        common_weak.sort(key=lambda x: x["weak_ratio"], reverse=True)

        # 个体差异（仅用样本充足的学生比较）
        accs = [s["accuracy"] for s in reliable_students]
        differences: Dict[str, Any] = {}
        if len(accs) >= 2:
            differences["accuracy"] = {
                "min": round(min(accs), 4),
                "max": round(max(accs), 4),
                "avg": round(statistics.mean(accs), 4),
                "median": round(statistics.median(accs), 4),
                "std": round(statistics.pstdev(accs), 4),
                "gap": round(max(accs) - min(accs), 4),
                "compared_students": len(accs),
                "evidence_text": (
                    f"在 {len(accs)} 名作答量充足的学生中，"
                    f"最高 {max(accs) * 100:.1f}%（{reliable_students[0]['name']}），"
                    f"最低 {min(accs) * 100:.1f}%（{reliable_students[-1]['name']}），"
                    f"相差 {(max(accs) - min(accs)) * 100:.1f} 个百分点，"
                    f"标准差 {statistics.pstdev(accs):.3f}"
                ),
            }
            atts = [s["attempts"] for s in judged_students]
            differences["attempts"] = {
                "min": min(atts),
                "max": max(atts),
                "avg": round(statistics.mean(atts), 1),
                "evidence_text": f"人均作答 {statistics.mean(atts):.1f} 次，最少 {min(atts)} 次、最多 {max(atts)} 次",
            }

        notable = []
        if len(reliable_students) >= 2:
            bottom = reliable_students[-1]
            gap = ((class_acc or 0) - bottom["accuracy"]) * 100
            if gap > 0:
                notable.append(
                    {
                        "type": "low",
                        "student_id": bottom["student_id"],
                        "student_name": bottom["name"],
                        "note": (
                            f"正确率 {bottom['accuracy'] * 100:.1f}%，低于班级均值 "
                            f"{(class_acc or 0) * 100:.1f}% 约 {gap:.0f} 个百分点，"
                            f"有 {bottom['attempts']} 次作答作为依据，结论可靠"
                        ),
                    }
                )
        # 样本不足的学生单独列出，明确不参与「谁最差」的判断
        for s in sparse_students:
            notable.append(
                {
                    "type": "insufficient",
                    "student_id": s["student_id"],
                    "student_name": s["name"],
                    "note": (
                        f"共 {s['attempts']} 次作答，分散在 {s['knowledge_points_practiced']} 个知识点上，"
                        f"没有单个知识点达到 {MIN_ATTEMPTS_FOR_JUDGEMENT} 次的判断门槛，"
                        "暂不能评价其掌握水平，需要补充练习记录"
                    ),
                }
            )

        # 维度可用性（对应「分析维度应与实际数据相匹配」）
        def ratio(cond) -> float:
            return round(sum(1 for r in valid if cond(r)) / len(valid), 3) if valid else 0.0

        dimension_check = [
            {
                "dimension": "知识点掌握（正确率）",
                "available_ratio": ratio(lambda r: bool(r.knowledge_point)),
                "usable": ratio(lambda r: bool(r.knowledge_point)) >= 0.6,
                "note": "按知识点聚合正确率，是本次分析的主维度",
            },
            {
                "dimension": "作答耗时",
                "available_ratio": ratio(lambda r: r.duration_seconds is not None),
                "usable": ratio(lambda r: r.duration_seconds is not None) >= 0.6,
                "note": "仅统计清洗后仍然合理的耗时，异常耗时已置空",
            },
            {
                "dimension": "题目难度",
                "available_ratio": 0.0,
                "usable": False,
                "note": "现有学情记录未采集难度字段，本次不做难度分层分析，避免臆造",
            },
            {
                "dimension": "错因归类",
                "available_ratio": 0.0,
                "usable": False,
                "note": "记录中没有错因标注，无法归纳错误类型；仅能给出「哪个知识点偏弱」，不能说明「为什么错」",
            },
        ]

        data_notes = list(q.notes)
        data_notes.append(
            f"共 {len(student_stats)} 名学生有可判断记录，累计 {total_attempts} 次作答；"
            f"班级整体正确率 {class_acc * 100:.1f}%" if class_acc is not None else "暂无可用作答记录"
        )
        unavailable = [d["dimension"] for d in dimension_check if not d["usable"]]
        if unavailable:
            data_notes.append(
                f"以下维度因数据未采集而不纳入本次分析：{'、'.join(unavailable)}。"
                "报告中不对这些维度下结论。"
            )
        if sparse_students:
            data_notes.append(
                f"{'、'.join(s['name'] for s in sparse_students[:5])} 的作答分散在多个知识点上，"
                f"没有任何一个知识点的作答次数达到 {MIN_ATTEMPTS_FOR_JUDGEMENT} 次，"
                "个体正确率只能看作偶然波动，**不参与班级排名与差异比较**。"
                "这不代表其学习落后，而是数据不足以判断。"
            )

        return {
            "course": course,
            "cohort": {
                "students_total": len(student_stats),
                "students_judged": len(judged_students),
                "students_reliable": len(reliable_students),
                "students_sparse": len(sparse_students),
                "total_attempts": total_attempts,
                "records_total": q.raw_count,
                "records_valid": len(valid),
                "avg_attempts": round(total_attempts / len(judged_students), 1) if judged_students else 0,
            },
            "overall": {"accuracy": class_acc},
            "knowledge_points": kp_summary,
            "common_weak_points": common_weak,
            "student_stats": judged_students,
            "differences": differences,
            "notable_cases": notable,
            "dimension_check": dimension_check,
            "data_notes": data_notes,
            "thresholds": {
                "min_attempts": MIN_ATTEMPTS_FOR_JUDGEMENT,
                "acc_weak": ACC_WEAK,
                "common_weak_ratio": COMMON_WEAK_RATIO,
            },
        }

    # ------------------------------------------------------------------
    # 导出
    # ------------------------------------------------------------------
    def render_markdown(self, kind: str, data: Dict[str, Any], quality: QualityResult) -> str:
        lines: List[str] = []
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        if kind == "group":
            course = data["course"]
            lines.append(f"# 《{course.get('name', '')}》班级学情分析报告")
        else:
            lines.append(f"# {data['student'].get('name', '')} 个人学情分析报告")
        lines.append("")
        lines.append(f"- **生成时间**：{stamp}")
        lines.append(f"- **数据来源**：平台学情记录（模拟数据，用于教学研究演示）")
        lines.append("")

        # ---- 数据质量 ----
        lines.append("## 一、数据整理与质量检查")
        lines.append("")
        lines.append(
            f"共读取原始记录 **{quality.raw_count}** 条，经清洗后保留有效记录 "
            f"**{quality.valid_count}** 条。各类问题及处理方式如下："
        )
        lines.append("")
        if quality.issues:
            lines.append("| 问题类型 | 具体问题 | 条数 | 处理方式 |")
            lines.append("|---|---|---:|---|")
            type_label = {"missing": "缺失", "abnormal": "异常", "duplicate": "重复"}
            for it in quality.issues:
                lines.append(
                    f"| {type_label.get(it['type'], it['type'])} | {it['title']} | {it['count']} | {it['handling']} |"
                )
        else:
            lines.append("本次数据未发现缺失、异常或重复问题，全部记录可直接用于分析。")
        lines.append("")
        lines.append("**处理过程（条数变化）**")
        lines.append("")
        lines.append("| 步骤 | 处理前 | 处理后 | 变化 |")
        lines.append("|---|---:|---:|---:|")
        for s in quality.steps:
            lines.append(f"| {s['step']} | {s['before']} | {s['after']} | -{s['removed']} |")
        lines.append("")
        for n in quality.notes:
            lines.append(f"> {n}")
        lines.append("")

        # ---- 正文 ----
        if kind == "group":
            lines.extend(self._md_group(data, skip_notes=set(quality.notes)))
        else:
            lines.extend(self._md_individual(data, skip_notes=set(quality.notes)))

        return "\n".join(lines)

    def _md_individual(self, d: Dict[str, Any], skip_notes: Optional[set] = None) -> List[str]:
        skip_notes = skip_notes or set()
        lines: List[str] = []
        o = d["overall"]
        sec = _SectionNumber(start=2)  # 第一节是数据质量检查
        lines.append(sec.title("学习情况摘要"))
        lines.append("")
        lines.append(f"- 有效作答：**{o['attempts']}** 次（可判断对错）")
        lines.append(f"- 覆盖知识点：**{o['knowledge_point_count']}** 个")
        if o["accuracy"] is not None:
            lines.append(f"- 整体正确率：**{o['accuracy'] * 100:.1f}%**（{o['accuracy_basis']}）")
        lines.append(f"- 练习跨度：**{o['practice_days']}** 天")
        if o.get("avg_duration_minutes"):
            lines.append(f"- 平均单次作答：**{o['avg_duration_minutes']}** 分钟")
        lines.append("")

        if d["needs_consolidation"]:
            lines.append(sec.title("需要巩固的内容"))
            lines.append("")
            lines.append("| 知识点 | 作答次数 | 正确次数 | 正确率 | 依据记录 |")
            lines.append("|---|---:|---:|---:|---|")
            for k in d["needs_consolidation"]:
                ids = "、".join(str(i) for i in k["evidence_record_ids"][:6])
                lines.append(
                    f"| {k['knowledge_point']} | {k['attempts']} | {k['correct_count']} | "
                    f"{k['accuracy'] * 100:.1f}% | #{ids} |"
                )
            lines.append("")

        if d["fair_areas"]:
            lines.append(sec.title("基本掌握、建议适度巩固的内容"))
            lines.append("")
            for k in d["fair_areas"]:
                lines.append(f"- **{k['knowledge_point']}**：{k['evidence_text']}")
            lines.append("")

        if d["strengths"]:
            lines.append(sec.title("已掌握较好的内容"))
            lines.append("")
            for k in d["strengths"]:
                lines.append(f"- **{k['knowledge_point']}**：{k['evidence_text']}（记录 #{'、#'.join(str(i) for i in k['evidence_record_ids'][:4])}）")
            lines.append("")

        if d["insufficient_evidence"]:
            lines.append(sec.title("信息不足、尚不能判断的内容"))
            lines.append("")
            lines.append(
                f"以下知识点的作答次数少于 {d['thresholds']['min_attempts']} 次，"
                "样本不足以判断掌握情况。**「记录少」不等于「没学会」**，"
                "可能是练习安排少或数据未采集完整，需要补做练习后再判断。"
            )
            lines.append("")
            for k in d["insufficient_evidence"]:
                lines.append(f"- **{k['knowledge_point']}**：仅 {k['attempts']} 次作答（{k['evidence_text']}）")
            lines.append("")

        lines.append(sec.title("说明"))
        lines.append("")
        for n in d["data_notes"]:
            if n in skip_notes:
                continue
            lines.append(f"- {n}")
        lines.append("")
        lines.append(
            f"> 判定口径：作答次数 ≥ {d['thresholds']['min_attempts']} 次才下结论；"
            f"正确率 ≥ {d['thresholds']['acc_good'] * 100:.0f}% 记为掌握良好，"
            f"< {d['thresholds']['acc_weak'] * 100:.0f}% 记为需巩固。"
        )
        return lines

    def _md_group(self, d: Dict[str, Any], skip_notes: Optional[set] = None) -> List[str]:
        skip_notes = skip_notes or set()
        lines: List[str] = []
        c = d["cohort"]
        sec = _SectionNumber(start=2)
        lines.append(sec.title("班级学习情况摘要"))
        lines.append("")
        lines.append(f"- 参与学生：**{c['students_total']}** 人，其中 **{c['students_judged']}** 人有可判断记录")
        lines.append(
            f"- 可用于横向比较：**{c.get('students_reliable', c['students_judged'])}** 人"
            + (
                f"（另有 {c['students_sparse']} 人作答量不足，单独说明、不参与排名）"
                if c.get("students_sparse")
                else ""
            )
        )
        lines.append(f"- 累计作答：**{c['total_attempts']}** 次，人均 **{c['avg_attempts']}** 次")
        if d["overall"]["accuracy"] is not None:
            lines.append(f"- 班级整体正确率：**{d['overall']['accuracy'] * 100:.1f}%**")
        lines.append("")

        lines.append(sec.title("共性问题（多名学生同时薄弱）"))
        lines.append("")
        if d["common_weak_points"]:
            lines.append("| 知识点 | 整体正确率 | 薄弱人数 | 薄弱占比 | 依据 |")
            lines.append("|---|---:|---:|---:|---|")
            for k in d["common_weak_points"]:
                lines.append(
                    f"| {k['knowledge_point']} | {k['accuracy'] * 100:.1f}% | {k['weak_students']} "
                    f"| {k['weak_ratio'] * 100:.0f}% | {k['evidence_text']} |"
                )
        else:
            lines.append("按当前口径（≥50% 学生正确率低于 60%）未发现共性薄弱点。")
        lines.append("")

        lines.append(sec.title("值得关注的差异"))
        lines.append("")
        if "accuracy" in d["differences"]:
            lines.append(f"- **正确率差异**：{d['differences']['accuracy']['evidence_text']}")
        if "attempts" in d["differences"]:
            lines.append(f"- **练习量差异**：{d['differences']['attempts']['evidence_text']}")
        lines.append("")
        if d["notable_cases"]:
            lines.append("需要重点关注：")
            lines.append("")
            for n in d["notable_cases"]:
                lines.append(f"- **{n['student_name']}**：{n['note']}")
            lines.append("")

        lines.append(sec.title("分析维度与实际数据的匹配情况"))
        lines.append("")
        lines.append("| 分析维度 | 数据可用率 | 是否采用 | 说明 |")
        lines.append("|---|---:|---|---|")
        for dim in d["dimension_check"]:
            lines.append(
                f"| {dim['dimension']} | {dim['available_ratio'] * 100:.0f}% | "
                f"{'采用' if dim['usable'] else '不采用'} | {dim['note']} |"
            )
        lines.append("")

        lines.append(sec.title("说明"))
        lines.append("")
        for n in d["data_notes"]:
            if n in skip_notes:
                continue
            lines.append(f"- {n}")
        lines.append("")
        lines.append(
            f"> 判定口径：单个知识点需 ≥ {d['thresholds']['min_attempts']} 次作答才下结论；"
            f"正确率 < {d['thresholds']['acc_weak'] * 100:.0f}% 记为薄弱；"
            f"≥ {d['thresholds']['common_weak_ratio'] * 100:.0f}% 的学生同时薄弱才认定为共性问题。"
        )
        return lines

    def render_docx(self, kind: str, data: Dict[str, Any], quality: QualityResult):
        """生成 Word 文档，返回 docx 的 bytes"""
        from io import BytesIO

        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.shared import Pt, RGBColor

        doc = Document()

        style = doc.styles["Normal"]
        style.font.name = "微软雅黑"
        style.font.size = Pt(10.5)

        if kind == "group":
            title = f"《{data['course'].get('name', '')}》班级学情分析报告"
        else:
            title = f"{data['student'].get('name', '')} 个人学情分析报告"
        h = doc.add_heading(title, level=0)
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER

        meta = doc.add_paragraph()
        meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = meta.add_run(
            f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}　｜　数据来源：平台学情记录（模拟数据）"
        )
        run.font.size = Pt(9)
        run.font.color.rgb = RGBColor(0x75, 0x75, 0x75)

        # 数据质量
        doc.add_heading("一、数据整理与质量检查", level=1)
        doc.add_paragraph(
            f"共读取原始记录 {quality.raw_count} 条，经清洗后保留有效记录 {quality.valid_count} 条。"
            "各类问题及处理方式见下表。"
        )
        if quality.issues:
            t = doc.add_table(rows=1, cols=4)
            t.style = "Light Grid Accent 1"
            for i, txt in enumerate(["问题类型", "具体问题", "条数", "处理方式"]):
                t.rows[0].cells[i].text = txt
            label = {"missing": "缺失", "abnormal": "异常", "duplicate": "重复"}
            for it in quality.issues:
                row = t.add_row().cells
                row[0].text = label.get(it["type"], it["type"])
                row[1].text = it["title"]
                row[2].text = str(it["count"])
                row[3].text = it["handling"]

        doc.add_paragraph("")
        doc.add_paragraph("处理过程（条数变化）：")
        if quality.steps:
            t2 = doc.add_table(rows=1, cols=4)
            t2.style = "Light List Accent 1"
            for i, txt in enumerate(["步骤", "处理前", "处理后", "变化"]):
                t2.rows[0].cells[i].text = txt
            for s in quality.steps:
                row = t2.add_row().cells
                row[0].text = s["step"]
                row[1].text = str(s["before"])
                row[2].text = str(s["after"])
                row[3].text = f"-{s['removed']}"

        for n in quality.notes:
            p = doc.add_paragraph(n, style="Intense Quote")

        # 正文：复用 markdown 的正文段落结构
        md_lines = (
            self._md_individual(data) if kind != "group" else self._md_group(data)
        )
        for line in md_lines:
            s = line.strip()
            if not s:
                continue
            if s.startswith("## "):
                doc.add_heading(s[3:].strip(), level=1)
            elif s.startswith("| "):
                continue  # 表格已在上面单独处理，正文里的 md 表格跳过
            elif s.startswith("- "):
                doc.add_paragraph(s[2:].replace("**", ""), style="List Bullet")
            elif s.startswith("> "):
                p = doc.add_paragraph(s[2:].replace("**", ""), style="Intense Quote")
            else:
                doc.add_paragraph(s.replace("**", ""))

        buf = BytesIO()
        doc.save(buf)
        return buf.getvalue()
