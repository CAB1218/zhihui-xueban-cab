"""
任务成果包导出脚本（智慧学伴 · 七年级数学赛题数据）

把平台「AI Agent 智能体」对已导入模拟学情数据完成分析后的全部结构化产出，
落盘为一个可机读、可交付的成果包。

对应赛题任务成果包要求：
    · 学习内容梳理      → 01_学习内容梳理/
    · 个体与群体学情分析 → 02_群体学情分析/ + 03_个体学情分析/
    · 个性化学习建议    → 04_个性化学习建议/
    · 典型案例          → 05_典型案例/
    · 输入输出样例      → 06_输入输出样例/
    · 结构化 JSON / CSV + 字段说明 + 操作说明

与线上页面完全同源：直接调用 LearningAnalysisService / LearningAdviceService，
不另写一套算法，避免"页面一套、成果包一套"。

用法（容器内）：
    python scripts/export_task_package.py
    python scripts/export_task_package.py --out /app/data/contest/任务成果包 --course 七年级数学

幂等：重跑会清空输出目录后重建。
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import async_session_factory
from app.models.contest import ContestCourseRequirement, ContestExamNode, ContestMaterial
from app.models.course import Course
from app.models.curriculum import CurriculumOutline
from app.models.user import User
from app.services.learning_advice_service import LearningAdviceService
from app.services.learning_analysis_service import LearningAnalysisService

TENANT_ID = 1
PACKAGE_NAME = "任务成果包"
GENERATOR = "智慧学伴 export_task_package.py v1.0"


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_csv(path: Path, rows: Iterable[Dict[str, Any]], headers: Optional[Sequence[str]] = None) -> int:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8-sig")
        return 0
    fieldnames = list(headers) if headers else list(rows[0].keys())
    # utf-8-sig：Excel 直接双击不乱码
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fieldnames})
    return len(rows)


def pct(x: Optional[float]) -> str:
    return "" if x is None else f"{round(x * 100, 1)}%"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clip(text: Optional[str], n: int = 200) -> str:
    if not text:
        return ""
    t = str(text).replace("\n", " ").strip()
    return t if len(t) <= n else t[: n - 1] + "…"


# ---------------------------------------------------------------------------
# 01 学习内容梳理
# ---------------------------------------------------------------------------
async def export_content(db, course: Course, records, out: Path) -> Dict[str, Any]:
    base = ensure_dir(out / "01_学习内容梳理")

    requirements = (
        await db.execute(
            select(ContestCourseRequirement)
            .where(ContestCourseRequirement.tenant_id == TENANT_ID)
            .order_by(ContestCourseRequirement.topic_code, ContestCourseRequirement.indicator_code)
        )
    ).scalars().all()

    materials = (
        await db.execute(
            select(ContestMaterial)
            .where(ContestMaterial.tenant_id == TENANT_ID)
            .order_by(ContestMaterial.material_code)
        )
    ).scalars().all()

    exam_nodes = (
        await db.execute(
            select(ContestExamNode)
            .where(ContestExamNode.tenant_id == TENANT_ID)
            .order_by(ContestExamNode.node_code)
        )
    ).scalars().all()

    outline_row = (
        await db.execute(
            select(CurriculumOutline).where(
                CurriculumOutline.tenant_id == TENANT_ID,
                CurriculumOutline.status == "completed",
                CurriculumOutline.model_name == "contest-import",
            ).order_by(CurriculumOutline.created_at.desc())
        )
    ).scalars().first()
    if outline_row is None:
        outline_row = (
            await db.execute(
                select(CurriculumOutline).where(
                    CurriculumOutline.tenant_id == TENANT_ID,
                    CurriculumOutline.status == "completed",
                    CurriculumOutline.course_query.ilike(f"%{course.name}%"),
                ).order_by(CurriculumOutline.created_at.desc())
            )
        ).scalars().first()
    outline = json.loads(outline_row.outline) if outline_row and outline_row.outline else {}

    # --- 课程大纲（结构化） ---
    write_json(base / "课程大纲.json", {
        "meta": {
            "course_id": course.id,
            "course_name": course.name,
            "subject": course.subject,
            "grade": course.grade,
            "outline_title": outline_row.title if outline_row else None,
            "outline_id": outline_row.id if outline_row else None,
            "generated_by": outline_row.model_name if outline_row else None,
            "generated_at": outline_row.created_at.isoformat() if outline_row and outline_row.created_at else None,
        },
        "outline": outline,
    })

    md = [f"# {course.name} · 学习内容梳理", ""]
    md.append(f"- 范围：{outline.get('scope', '')}")
    if outline.get("scope_included"):
        md.append(f"- 纳入：{'、'.join(outline['scope_included'])}")
    if outline.get("scope_excluded"):
        md.append(f"- 不纳入：{'、'.join(outline['scope_excluded'])}")
    md.append("")
    for idx, unit in enumerate(outline.get("units", []), 1):
        md.append(f"## {idx}. {unit.get('name')}")
        md.append("")
        if unit.get("description"):
            md.append(f"> {unit['description']}")
            md.append("")
        if unit.get("textbook_ref"):
            md.append(f"- 教材位置：{unit['textbook_ref']}")
        md.append("")
        md.append("| # | 内容要点 | 要求水平 | 认知层次 | 建议课时 |")
        md.append("|---|---|---|---|---|")
        for j, c in enumerate(unit.get("contents", []), 1):
            md.append(
                f"| {j} | {c.get('topic','')} | {c.get('requirement_level','')} | "
                f"{c.get('cognitive_level','')} | {c.get('suggested_hours','')} |"
            )
        md.append("")
    write_text(base / "课程大纲.md", "\n".join(md))

    # --- 内容要求（CSV / JSON 双份，机读 + 人读） ---
    req_rows = [{
        "课标要求编号": r.cr_code,
        "主题编号": r.topic_code,
        "主题": r.topic,
        "主题目标": r.topic_goal,
        "指标编号": r.indicator_code,
        "观察指标": r.indicator,
        "课标页码": r.cr_pages,
        "教材页码": r.textbook_pages,
    } for r in requirements]
    write_csv(base / "内容要求.csv", req_rows)
    write_json(base / "内容要求.json", req_rows)

    # --- 知识点结构：观察指标 + 所属主题 + 题目量 + 群体正确率 ---
    by_kp: Dict[str, List] = {}
    for r in records:
        if r.knowledge_point and r.judgeable:
            by_kp.setdefault(r.knowledge_point, []).append(r)
    q_count: Dict[str, int] = {}
    for m in materials:
        if m.material_type == "题目" and m.indicator_code:
            # indicator_code → 指标名称
            name = next((x.indicator for x in requirements if x.indicator_code == m.indicator_code), None)
            if name:
                q_count[name] = q_count.get(name, 0) + 1

    kp_rows = []
    for r in requirements:
        recs = by_kp.get(r.indicator, [])
        correct = sum(1 for x in recs if x.correct)
        kp_rows.append({
            "观察指标": r.indicator,
            "指标编号": r.indicator_code,
            "主题编号": r.topic_code,
            "主题": r.topic,
            "课标要求编号": r.cr_code,
            "教材页码": r.textbook_pages,
            "配套题目数": q_count.get(r.indicator, 0),
            "作答记录数": len(recs),
            "群体正确率": pct(correct / len(recs)) if recs else "",
        })
    write_csv(base / "知识点结构.csv", kp_rows)

    # --- 测验节点 ---
    node_rows = [{
        "节点编号": n.node_code,
        "考试日期": n.exam_date.isoformat() if n.exam_date else "",
        "覆盖主题": n.taught_topics,
        "说明": n.note,
        "题目数": len((n.question_codes or "").split("、")) if n.question_codes else 0,
        "题目编号": n.question_codes,
    } for n in exam_nodes]
    write_csv(base / "测验节点.csv", node_rows)
    write_json(base / "测验节点.json", node_rows)

    # --- 题目与材料 ---
    mat_rows = [{
        "材料编号": m.material_code,
        "类型": m.material_type,
        "主题编号": m.topic_code,
        "题型": m.question_type,
        "指标编号": m.indicator_code,
        "分值": m.max_score,
        "内容": m.content,
        "选项": m.options,
        "答案": m.answer,
        "解析": m.analysis,
        "评分点": m.grading_points,
        "来源文件": m.source_file,
    } for m in materials]
    write_csv(base / "题目与材料.csv", mat_rows)

    return {
        "outline_units": len(outline.get("units", [])),
        "requirements": len(req_rows),
        "knowledge_points": len(kp_rows),
        "exam_nodes": len(node_rows),
        "materials": len(mat_rows),
    }


# ---------------------------------------------------------------------------
# 02 群体学情分析
# ---------------------------------------------------------------------------
async def export_group(db, course: Course, records, students, quality, out: Path) -> Dict[str, Any]:
    base = ensure_dir(out / "02_群体学情分析")
    svc = LearningAnalysisService(db)

    course_dict = {"id": course.id, "name": course.name, "subject": course.subject, "grade": course.grade}
    data = svc.group_summary(records, course_dict, students=students, quality=quality)
    data["quality"] = {
        "raw_count": quality.raw_count,
        "valid_count": quality.valid_count,
        "counts": quality.counts,
        "issues": quality.issues,
        "steps": quality.steps,
        "notes": quality.notes,
    }
    data["meta"] = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "generator": GENERATOR,
        "course_id": course.id,
        "course_name": course.name,
        "tenant_id": TENANT_ID,
    }
    write_json(base / "群体学情摘要.json", data)
    write_text(base / "群体学情摘要.md", svc.render_markdown("group", data, quality))

    # 知识点掌握表
    kp_rows = [{
        "知识点": k["knowledge_point"],
        "作答学生数": k["students_practiced"],
        "作答次数": k["attempts"],
        "正确率": pct(k.get("accuracy")),
        "薄弱学生数": k["weak_students"],
        "薄弱占比": pct(k.get("weak_ratio")),
        "是否共性薄弱": "是" if k.get("is_common_weak") else "否",
    } for k in data.get("knowledge_points", [])]
    write_csv(base / "知识点掌握.csv", kp_rows)

    # 学生横向对比表（含个体关键指标 + 建议条数，后面回填）
    comp_rows = []
    for s in data.get("student_stats", []):
        info = students.get(s["student_id"], {})
        comp_rows.append({
            "学生编号": f"S{s['student_id']:03d}",
            "姓名": s["name"],
            "班级": info.get("class_code") or "",
            "作答次数": s["attempts"],
            "正确数": s["correct_count"],
            "正确率": pct(s.get("accuracy")),
            "覆盖知识点数": s["knowledge_points_practiced"],
            "可靠判定知识点数": s["reliable_kp_count"],
        })
    write_csv(base / "学生横向对比.csv", comp_rows)

    # 数据质量问题明细
    issues = []
    for i in data["quality"]["issues"]:
        issues.append({
            "问题类型": i.get("title") or i.get("type"),
            "问题代码": i.get("code"),
            "条数": i.get("count"),
            "涉及记录ID(前20)": "、".join(str(x) for x in (i.get("record_ids") or [])[:20]),
            "判定说明": i.get("detail"),
            "处理方式": i.get("handling"),
            "处理类型": i.get("handling_type"),
        })
    write_csv(base / "数据质量问题.csv", issues)

    # 清洗步骤（before/after，可追溯）
    write_csv(base / "数据清洗步骤.csv", [
        {"步骤": s.get("step"), "处理前": s.get("before"), "处理后": s.get("after"), "剔除": s.get("removed")}
        for s in data["quality"].get("steps", [])
    ])

    # 维度可用性
    write_csv(base / "维度可用性.csv", [
        {
            "分析维度": d.get("dimension"),
            "可用比例": pct(d.get("available_ratio")),
            "是否纳入分析": "是" if d.get("usable") else "否",
            "说明": d.get("note"),
        }
        for d in data.get("dimension_check", [])
    ])

    return {"group": data, "rows": len(comp_rows)}


# ---------------------------------------------------------------------------
# 03 个体学情 + 04 个性化建议
# ---------------------------------------------------------------------------
async def export_individual_and_advice(
    db, course: Course, records, students, quality, out: Path
) -> Dict[str, Any]:
    ind_dir = ensure_dir(out / "03_个体学情分析")
    plan_dir = ensure_dir(out / "04_个性化学习建议")
    ind_json = ensure_dir(ind_dir / "json")
    ind_md = ensure_dir(ind_dir / "md")
    plan_json = ensure_dir(plan_dir / "json")
    plan_md = ensure_dir(plan_dir / "md")

    analysis = LearningAnalysisService(db)
    advice = LearningAdviceService(db)
    course_dict = {"id": course.id, "name": course.name, "subject": course.subject, "grade": course.grade}

    by_student: Dict[int, List] = {}
    for r in records:
        by_student.setdefault(r.student_id, []).append(r)

    index_rows, plan_rows = [], []
    # 按学生编号（昵称 D01…）排序，便于人工核对
    ordered = sorted(students.values(), key=lambda s: s.get("name") or "")

    for stu in ordered:
        sid = stu["student_id"]
        recs = by_student.get(sid, [])
        brief = {
            "id": sid,
            "name": stu.get("name"),
            "grade": stu.get("grade"),
            "major": stu.get("major"),
        }
        code = f"S{sid:03d}"
        label = stu.get("name") or code

        # --- 个体学情 ---
        sq = analysis.check_quality(recs)
        ind = analysis.individual_summary(recs, brief, sq, course.name)
        ind["meta"] = {
            "student_code": code,
            "class_code": stu.get("class_code"),
            "course_id": course.id,
            "course_name": course.name,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "generator": GENERATOR,
        }
        ind["quality"] = {
            "raw_count": sq.raw_count,
            "valid_count": sq.valid_count,
            "counts": sq.counts,
            "issues": sq.issues,
        }
        write_json(ind_json / f"{code}_{label}_学情摘要.json", ind)
        write_text(ind_md / f"{code}_{label}_学情分析.md", analysis.render_markdown("individual", ind, sq))

        # --- 个性化学习建议 ---
        plan = await advice.build_plan(
            tenant_id=TENANT_ID,
            student=brief,
            course=course_dict,
            records=recs,
            cohort_records=records,
            duration_days=7,
        )
        plan["meta"] = {
            "student_code": code,
            "class_code": stu.get("class_code"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "generator": GENERATOR,
        }
        write_json(plan_json / f"{code}_{label}_学习建议.json", plan)
        write_text(plan_md / f"{code}_{label}_学习建议.md", advice.render_markdown(plan))

        overall = ind.get("overall", {})
        targets = [f"{i['order']}.{i['knowledge_point']}" for i in plan.get("items", [])]
        weak = [x["knowledge_point"] for x in ind.get("needs_consolidation", [])]

        index_rows.append({
            "学生编号": code,
            "姓名": label,
            "班级": stu.get("class_code") or "",
            "有效记录数": overall.get("records_valid"),
            "可判定作答次数": overall.get("attempts"),
            "正确率": pct(overall.get("accuracy")),
            "覆盖知识点数": overall.get("knowledge_point_count"),
            "掌握良好": sum(1 for k in ind.get("knowledge_points", []) if k.get("status") == "good"),
            "基本掌握": sum(1 for k in ind.get("knowledge_points", []) if k.get("status") == "fair"),
            "需巩固": len(ind.get("needs_consolidation", [])),
            "证据不足": len(ind.get("insufficient_evidence", [])),
            "薄弱知识点": "；".join(weak[:4]),
            "证据充分": "是" if plan.get("summary", {}).get("student_evidence_sufficient") else "否",
            "建议条数": len(plan.get("items", [])),
            "建议覆盖知识点": "；".join(targets),
            "预计总时长(分钟)": sum(int(i.get("estimated_minutes") or 0) for i in plan.get("items", [])),
            "排期天数": len(plan.get("schedule", [])),
        })
        plan_rows.append({
            "学生编号": code,
            "姓名": label,
            "班级": stu.get("class_code") or "",
            "正确率": pct(overall.get("accuracy")),
            "建议条数": len(plan.get("items", [])),
            "目标知识点": "；".join(targets),
            "观察项数": len(plan.get("observation_items", [])),
            "预计总时长(分钟)": sum(int(i.get("estimated_minutes") or 0) for i in plan.get("items", [])),
            "大纲可用": "是" if plan.get("outline", {}).get("available") else "否",
            "引用资源数": plan.get("resources_checked"),
            "生成引擎": plan.get("engine"),
        })

    write_csv(ind_dir / "学生索引.csv", index_rows)
    write_csv(plan_dir / "建议总览.csv", plan_rows)
    write_json(ind_dir / "学生索引.json", index_rows)

    return {"students": len(index_rows), "index_rows": index_rows}


# ---------------------------------------------------------------------------
# 05 典型案例（取群体分析中的 notable_cases）
# ---------------------------------------------------------------------------
CASE_LABEL = {
    "high": ("案例一_掌握良好型", "整体正确率较高，用于示范「保持 + 拔高」型建议"),
    "low": ("案例二_基础薄弱型", "正确率明显低于群体均值，用于示范「补基础 + 降台阶」型建议"),
    "insufficient": ("案例三_证据不足型", "作答量少或分散，用于示范「先补观察、不硬下结论」型建议"),
}


def pick_cases(group: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从群体统计里挑 3 个典型学生：掌握良好 / 基础薄弱 / 证据不足。

    不直接照搬 notable_cases，因为其中只保证「最弱」与「样本不足」两类，
    缺「掌握良好」这一正面样例；这里补齐并去重。
    """
    stats = [s for s in group.get("student_stats", []) if s.get("attempts")]
    # 只有「至少 1 个知识点达到判断门槛」的学生才谈得上「掌握良好/薄弱」，
    # 否则 3 次作答 100% 也会被误当成高位样例
    reliable = [
        s for s in stats
        if s.get("accuracy") is not None
        and s.get("attempts", 0) >= 5
        and s.get("reliable_kp_count", 0) >= 1
    ]
    picked: List[Dict[str, Any]] = []
    used: set = set()

    def add(ctype: str, s: Optional[Dict[str, Any]], note: str) -> None:
        if not s or s["student_id"] in used:
            return
        used.add(s["student_id"])
        picked.append({
            "type": ctype,
            "student_id": s["student_id"],
            "student_name": s.get("name"),
            "note": note,
        })

    if reliable:
        # 高位/低位样例优先取作答量 ≥10 次的学生，避免「3 次全对」被当成掌握良好
        pool = [s for s in reliable if s.get("attempts", 0) >= 10] or reliable
        best = max(pool, key=lambda s: (s["accuracy"], s["attempts"]))
        add(
            "high",
            best,
            f"正确率 {pct(best['accuracy'])}，{best['attempts']} 次作答、覆盖 "
            f"{best.get('knowledge_points_practiced')} 个知识点，是群体中的高位样例",
        )
        worst = min(pool, key=lambda s: (s["accuracy"], -s["attempts"]))
        class_acc = (group.get("overall") or {}).get("accuracy")
        gap = (class_acc - worst["accuracy"]) * 100 if class_acc is not None else None
        add(
            "low",
            worst,
            f"正确率 {pct(worst['accuracy'])}"
            + (f"，低于群体均值 {pct(class_acc)} 约 {gap:.0f} 个百分点" if gap is not None else "")
            + f"，有 {worst['attempts']} 次作答作为依据",
        )

    # 证据不足：优先取群体分析已标记的 insufficient，其次取作答最少者
    free = [s for s in stats if s["student_id"] not in used]
    thin = min(free, key=lambda s: (s.get("attempts") or 0, s.get("reliable_kp_count") or 0)) if free else None
    insufficient = [c for c in group.get("notable_cases", []) if c.get("type") == "insufficient"]
    marked = None
    for c in insufficient:
        marked = next((x for x in stats if x["student_id"] == c["student_id"] and x["student_id"] not in used), None)
        if marked is not None:
            add("insufficient", marked, c.get("note") or "")
            break
    if marked is None and thin is not None:
        add(
            "insufficient",
            thin,
            f"仅 {thin.get('attempts')} 次作答、可靠判定的知识点 {thin.get('reliable_kp_count')} 个，"
            "未达判断门槛，只能给出「补充观察」型方案",
        )
    return picked


async def export_cases(db, course: Course, records, students, group: Dict[str, Any], out: Path) -> Dict[str, Any]:
    base = ensure_dir(out / "05_典型案例")
    analysis = LearningAnalysisService(db)
    advice = LearningAdviceService(db)
    course_dict = {"id": course.id, "name": course.name, "subject": course.subject, "grade": course.grade}

    by_student: Dict[int, List] = {}
    for r in records:
        by_student.setdefault(r.student_id, []).append(r)

    cases = pick_cases(group)
    written = []
    summary_lines = ["# 典型案例说明", "", "以下 3 个案例由群体分析自动挑出（覆盖「掌握良好 / 基础薄弱 / 证据不足」三类典型状态），"
                     "每个案例包含个体学情分析报告与个性化学习建议，可直接作为任务三的举证材料。", ""]

    for idx, c in enumerate(cases, 1):
        ctype = c.get("type") or "case"
        sid = c.get("student_id")
        if not sid:
            continue
        title, purpose = CASE_LABEL.get(ctype, (f"案例{idx}", c.get("note") or ""))
        stu = students.get(sid, {})
        brief = {"id": sid, "name": c.get("student_name") or stu.get("name"), "grade": stu.get("grade"), "major": stu.get("major")}
        recs = by_student.get(sid, [])
        if not recs:
            continue

        sq = analysis.check_quality(recs)
        ind = analysis.individual_summary(recs, brief, sq, course.name)
        plan = await advice.build_plan(
            tenant_id=TENANT_ID, student=brief, course=course_dict,
            records=recs, cohort_records=records, duration_days=7,
        )

        stem = f"{title}_{brief['name']}"
        write_text(base / f"{stem}_学情分析.md", analysis.render_markdown("individual", ind, sq))
        write_text(base / f"{stem}_学习建议.md", advice.render_markdown(plan))
        write_json(base / f"{stem}.json", {
            "case_type": ctype,
            "case_title": title,
            "case_purpose": purpose,
            "note": c.get("note"),
            "student": brief,
            "individual_analysis": ind,
            "learning_plan": plan,
        })

        # Word 版，便于直接贴进申报材料
        try:
            docx_ind = analysis.render_docx("individual", ind, sq)
            (base / f"{stem}_学情分析.docx").write_bytes(docx_ind)
        except Exception as exc:  # noqa: BLE001
            summary_lines.append(f"> 提示：{stem} 的 docx 生成失败（{exc}），已提供 md 版本。")

        overall = ind.get("overall", {})
        summary_lines += [
            f"## {title}：{brief['name']}",
            "",
            f"- 选取依据：{c.get('note') or purpose}",
            f"- 数据基础：有效记录 {overall.get('records_valid')} 条 / 可判定作答 {overall.get('attempts')} 次 / 正确率 {pct(overall.get('accuracy'))}",
            f"- 需巩固知识点：{'、'.join(x['knowledge_point'] for x in ind.get('needs_consolidation', [])) or '无'}",
            f"- 建议目标：{'、'.join(i['knowledge_point'] for i in plan.get('items', [])) or '无'}",
            f"- 文件：`{stem}_学情分析.md` / `{stem}_学习建议.md` / `{stem}.json`",
            "",
        ]
        written.append(stem)

    write_text(base / "案例说明.md", "\n".join(summary_lines))
    return {"cases": written}


# ---------------------------------------------------------------------------
# 06 输入输出样例
# ---------------------------------------------------------------------------
async def export_samples(db, records, students, out: Path) -> Dict[str, Any]:
    from app.models.learning_record import LearningRecord

    base = ensure_dir(out / "06_输入输出样例")

    # 输入样例：挑作答量充足的一名学生，取前 20 条原始记录（含 raw_payload）
    counts: Dict[int, int] = {}
    for r in records:
        counts[r.student_id] = counts.get(r.student_id, 0) + 1
    sample_sid = max((sid for sid, n in counts.items() if n >= 20), key=lambda s: counts[s])
    rows_db = (
        await db.execute(
            select(LearningRecord)
            .where(
                LearningRecord.tenant_id == TENANT_ID,
                LearningRecord.student_id == sample_sid,
            )
            .order_by(LearningRecord.id)
            .limit(20)
        )
    ).scalars().all()

    rows = []
    for r in rows_db:
        raw = r.raw_payload or {}
        if not isinstance(raw, dict):
            raw = {}
        rows.append({
            "record_id": r.id,
            "学生编号": students.get(sample_sid, {}).get("name"),
            "班级": raw.get("班级") or students.get(sample_sid, {}).get("class_code") or "",
            "材料编号": raw.get("材料编号") or r.source_ref,
            "知识点": r.knowledge_point,
            "题型": raw.get("题型") or "",
            "满分": r.max_score,
            "得分": r.score,
            "是否作答正确": "" if r.is_correct is None else int(bool(r.is_correct)),
            "作答时间": raw.get("作答时间") or (r.recorded_at.isoformat() if r.recorded_at else ""),
            "耗时秒": r.duration_seconds,
            "解答过程": clip(raw.get("解答过程"), 120),
            "评分点得分": clip(raw.get("评分点得分"), 120),
        })
    write_csv(base / "输入_作答记录样例.csv", rows)

    write_text(base / "输入_字段说明.md", "\n".join([
        "# 输入样例字段说明（作答记录）",
        "",
        "来源：赛题 `作答记录.csv`，经 `scripts/import_contest_data.py` 导入后写入 `learning_records`。",
        "",
        "| 字段 | 类型 | 必填 | 说明 | 取值范围 / 示例 |",
        "|---|---|---|---|---|",
        "| record_id | int | 是 | 平台记录主键，成果包中所有 `evidence_record_ids` 指向它 | 826 |",
        "| 学生编号 | str | 是 | 学生昵称，D01—D40 | D01 |",
        "| 班级 | str | 否 | 赛题班级编码 | DC01 / DC02 |",
        "| 材料编号 | str | 是 | 题目/学习卡编号，对应 `01_学习内容梳理/题目与材料.csv` | Q014 / L02 / B03 |",
        "| 知识点 | str | 是 | 观察指标名称，个体/群体分析按此聚合 | 识别同类项、去括号并化简 |",
        "| 题型 | str | 否 | 选择题 / 填空题 / 解答题 等 | 解答题 |",
        "| 满分 | int | 否 | 该题满分 | 5 |",
        "| 得分 | float | 否 | 学生实际得分；>满分记为异常 | 3 |",
        "| 是否作答正确 | 0/1 | 否 | 由得分与满分推导；为空表示不可判定 | 1 |",
        "| 作答时间 | datetime | 否 | 赛题原始作答时刻；重复判定依据之一 | 2026-01-12 10:33:00 |",
        "| 耗时秒 | int | 否 | **赛题数据未提供该字段，全为空**，故「作答耗时」维度不纳入分析 | (空) |",
        "| 解答过程 | str | 否 | 主观题作答文本（节选 120 字） | 去括号得 3x-2x+4… |",
        "| 评分点得分 | str | 否 | 分步赋分明细（节选） | 去括号2/2；合并1/2 |",
        "",
        "> 说明：平台内部还会保留 `raw_payload`（赛题原始整行）以便溯源，样例中已展开为上方列。",
    ]))

    # 输出样例：与输入样例取同一名学生，便于对照「同一条数据进 → 什么结果出」
    pkg = out
    sample_name = students.get(sample_sid, {}).get("name") or ""
    ind_files = sorted((pkg / "03_个体学情分析" / "json").glob(f"*{sample_name}_学情摘要.json"))
    if ind_files:
        shutil.copyfile(ind_files[0], base / "输出_个体学情摘要样例.json")
    plan_files = sorted((pkg / "04_个性化学习建议" / "json").glob(f"*{sample_name}_学习建议.json"))
    if plan_files:
        shutil.copyfile(plan_files[0], base / "输出_学习建议样例.json")
    grp = pkg / "02_群体学情分析" / "群体学情摘要.json"
    if grp.exists():
        shutil.copyfile(grp, base / "输出_群体学情摘要样例.json")

    write_text(base / "样例说明.md", "\n".join([
        "# 输入输出样例说明",
        "",
        "本目录给出「输入是什么 → 输出长什么样」的最小可核对样例，便于验收方不复现环境也能判断格式是否符合要求。",
        "",
        "| 文件 | 作用 |",
        "|---|---|",
        "| `输入_作答记录样例.csv` | 20 条原始作答记录（同一学生连续节选），即平台接收的输入形态 |",
        "| `输入_字段说明.md` | 上述输入的逐字段说明，含「赛题缺失字段如何标注」 |",
        "| `输出_个体学情摘要样例.json` | 以输入样例同一名学生为准的个体学情输出（与 `03_个体学情分析/json/` 完全一致） |",
        "| `输出_学习建议样例.json` | 该学生的 7 天个性化学习建议输出 |",
        "| `输出_群体学情摘要样例.json` | 全体 40 人的群体学情输出 |",
        "",
        "字段级定义见上级目录 `字段说明.md`。",
    ]))

    return {"sample_student": students.get(sample_sid, {}).get("name"), "rows": len(rows)}


# ---------------------------------------------------------------------------
# manifest
# ---------------------------------------------------------------------------
def build_manifest(root: Path, stats: Dict[str, Any]) -> None:
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.name != "manifest.json":
            files.append({
                "path": p.relative_to(root).as_posix(),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_of(p),
            })
    manifest = {
        "package": PACKAGE_NAME,
        "generator": GENERATOR,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": {
            "tenant_id": TENANT_ID,
            "course": "七年级数学（赛题模拟学情数据）",
            "data_origin": "赛题 CSV + 课程标准 PDF，经 scripts/import_contest_data.py 导入",
        },
        "stats": stats,
        "counts": {
            "files": len(files),
            "total_bytes": sum(f["size_bytes"] for f in files),
        },
        "files": files,
    }
    write_json(root / "manifest.json", manifest)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
async def main() -> None:
    parser = argparse.ArgumentParser(description="导出智慧学伴任务成果包")
    parser.add_argument("--out", default=f"/app/data/contest/{PACKAGE_NAME}", help="输出目录")
    parser.add_argument("--course", default="七年级数学", help="课程名称")
    parser.add_argument(
        "--docs",
        default="/app/data/contest/成果包文档",
        help="说明文档目录（README/字段说明 等 *.md），存在则复制到成果包根目录",
    )
    args = parser.parse_args()

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    async with async_session_factory() as db:
        course = (
            await db.execute(select(Course).where(Course.name == args.course))
        ).scalars().first()
        if course is None:
            raise SystemExit(f"未找到课程：{args.course}")

        analysis = LearningAnalysisService(db)
        records = await analysis.load_records(TENANT_ID, course.id)
        if not records:
            raise SystemExit("该课程暂无学情记录")

        roster = await analysis.list_students(TENANT_ID)
        users = (
            await db.execute(select(User).where(User.id.in_([s["student_id"] for s in roster])))
        ).scalars().all()
        prefs: Dict[int, Dict[str, Any]] = {}
        for u in users:
            raw = u.preferences
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except ValueError:
                    raw = {}
            prefs[u.id] = raw if isinstance(raw, dict) else {}

        students: Dict[int, Dict[str, Any]] = {}
        for s in roster:
            item = dict(s)
            item["class_code"] = prefs.get(s["student_id"], {}).get("class_code")
            students[s["student_id"]] = item

        quality = analysis.check_quality(records)
        print(f"[0] 数据就绪：记录 {len(records)} 条，学生 {len(students)} 人")

        s1 = await export_content(db, course, records, out)
        print(f"[1] 学习内容梳理：{s1}")

        s2 = await export_group(db, course, records, students, quality, out)
        print(f"[2] 群体学情：{s2['rows']} 人纳入横向对比")

        s3 = await export_individual_and_advice(db, course, records, students, quality, out)
        print(f"[3] 个体学情 + 建议：{s3['students']} 份")

        s4 = await export_cases(db, course, records, students, s2["group"], out)
        print(f"[4] 典型案例：{s4['cases']}")

        s5 = await export_samples(db, records, students, out)
        print(f"[5] 输入输出样例：{s5}")

        docs_dir = Path(args.docs)
        doc_count = 0
        if docs_dir.exists():
            for p in sorted(docs_dir.glob("*.md")):
                shutil.copyfile(p, out / p.name)
                doc_count += 1
        print(f"[6] 说明文档：{doc_count} 份")

        build_manifest(out, {
            "content": s1,
            "group_students": s2["rows"],
            "students": s3["students"],
            "cases": len(s4["cases"]),
            "quality": {
                "raw_count": quality.raw_count,
                "valid_count": quality.valid_count,
                "counts": quality.counts,
            },
        })
        print(f"[7] 清单已写入，成果包路径：{out}")


if __name__ == "__main__":
    asyncio.run(main())
