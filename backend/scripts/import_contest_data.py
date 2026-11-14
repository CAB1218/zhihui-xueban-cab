"""
赛题数据导入脚本（七年级数学 · 模拟学情数据）

把赛题提供的模拟学情数据导入平台，替换掉 seed_learning_records.py 随机生成的演示数据：

  模拟学生.csv    → users（D01—D40，班级写入 preferences.class_code）+ 选课
  作答记录.csv    → learning_records（806 条，raw_payload 保留赛题原始字段）
  课程要求.csv    → contest_course_requirements + 生成一份 CurriculumOutline（课程梳理成果）
  测验节点.csv    → contest_exam_nodes
  题目与材料.csv  → contest_materials（Q001—Q054 / L01—L03 / B01—B08）
  PDF 资源        → MinIO（contest/ 前缀）+ resources 表

幂等：重复执行会先清掉上一次导入的数据再重建，可安全重跑。

用法（容器内）：
    python scripts/import_contest_data.py
    python scripts/import_contest_data.py --data-dir /app/data/contest

数据目录约定（默认 /app/data/contest）：
    模拟学情数据/模拟学生.csv 等 6 个 CSV
    PDF 文件放在数据目录根部（课程标准_2022.pdf、B01—B08_相关资料切片.pdf）
"""
import argparse
import asyncio
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app.config import settings
from app.core.security import hash_password
from app.database import async_session_factory
from app.models.contest import ContestCourseRequirement, ContestExamNode, ContestMaterial
from app.models.course import Course, CourseEnrollment
from app.models.curriculum import CurriculumOutline
from app.models.learning_record import LearningRecord
from app.models.resource import Resource
from app.models.tenant import Tenant
from app.models.user import User

# 旧演示数据里的 10 个随机学生（seed_learning_records.py 生成），导入赛题数据时移除
LEGACY_MOCK_EMAILS = [
    "chenjiahe@student.ai4edu.com", "lisiyuan@student.ai4edu.com",
    "wangyutong@student.ai4edu.com", "zhanghaoran@student.ai4edu.com",
    "liuxinran@student.ai4edu.com", "zhaozimo@student.ai4edu.com",
    "sunyue@student.ai4edu.com", "zhoujingxing@student.ai4edu.com",
    "wusitong@student.ai4edu.com", "zhengke@student.ai4edu.com",
]

COURSE_NAME = "七年级数学"
STUDENT_PASSWORD = "student123"

PDF_FILES = [
    ("课程标准_2022.pdf", "义务教育数学课程标准（2022年版）", "curriculum_standard", None),
    ("B01_相关资料切片.pdf", "教材切片 B01（人教版七年级）", "textbook", "B01"),
    ("B02_相关资料切片.pdf", "教材切片 B02（人教版七年级）", "textbook", "B02"),
    ("B03_相关资料切片.pdf", "教材切片 B03（人教版七年级）", "textbook", "B03"),
    ("B04_相关资料切片.pdf", "教材切片 B04（人教版七年级）", "textbook", "B04"),
    ("B05_相关资料切片.pdf", "教材切片 B05（人教版七年级）", "textbook", "B05"),
    ("B06_相关资料切片.pdf", "教材切片 B06（人教版七年级）", "textbook", "B06"),
    ("B07_相关资料切片.pdf", "教材切片 B07（人教版七年级）", "textbook", "B07"),
    ("B08_相关资料切片.pdf", "教材切片 B08（人教版七年级）", "textbook", "B08"),
]


def read_csv(path: Path) -> list[dict]:
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            with open(path, encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别编码: {path}")


def parse_dt(s: str) -> datetime | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s).replace(tzinfo=None)  # 北京时间，存无时区
    except ValueError:
        return None


def parse_int(s: str) -> int | None:
    s = (s or "").strip()
    return int(s) if s.isdigit() else None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="/app/data/contest", help="赛题数据目录")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)
    csv_dir = data_dir / "模拟学情数据"
    if not csv_dir.exists():
        print(f"✗ 数据目录不存在: {csv_dir}")
        sys.exit(1)

    # ---------------- 预读 CSV ----------------
    students_csv = read_csv(csv_dir / "模拟学生.csv")
    reqs_csv = read_csv(csv_dir / "课程要求.csv")
    nodes_csv = read_csv(csv_dir / "测验节点.csv")
    materials_csv = read_csv(csv_dir / "题目与材料.csv")
    answers_csv = read_csv(csv_dir / "作答记录.csv")

    # 指标编号 → (指标文本, 主题编号, 主题名)
    indicator_map = {
        r["指标编号"].strip(): (r["观察指标"].strip(), r["主题编号"].strip(), r["主题"].strip())
        for r in reqs_csv
    }
    # 材料编号 → 题目行
    material_map = {r["材料编号"].strip(): r for r in materials_csv}
    # 学生编号 → 班级
    class_map = {r["学生编号"].strip(): r["模拟班级编号"].strip() for r in students_csv}

    print(f"✓ CSV 读取完成: 学生 {len(students_csv)} / 课程要求 {len(reqs_csv)} / "
          f"测验节点 {len(nodes_csv)} / 材料 {len(materials_csv)} / 作答 {len(answers_csv)}")

    async with async_session_factory() as db:
        tenant = (await db.execute(select(Tenant).order_by(Tenant.id))).scalars().first()
        if tenant is None:
            print("✗ 未找到租户，请先执行 seed_data.py")
            return
        tenant_id = tenant.id

        admin = (
            await db.execute(select(User).where(User.email == "admin@ai4edu.com"))
        ).scalars().first()
        if admin is None:
            print("✗ 未找到 admin@ai4edu.com，请先执行 seed_data.py")
            return

        # ---------------- 1. 清除旧数据（随机演示数据 + 上次导入） ----------------
        r = await db.execute(delete(LearningRecord).where(LearningRecord.is_simulated.is_(True)))
        print(f"✓ 清除旧学情记录（is_simulated=True）: {r.rowcount} 条")

        legacy_users = (
            await db.execute(
                select(User).where(
                    (User.email.in_(LEGACY_MOCK_EMAILS))
                    | (User.email.like("d__@student.ai4edu.com"))
                )
            )
        ).scalars().all()
        legacy_ids = [u.id for u in legacy_users]
        if legacy_ids:
            # 先清各业务表对这些学生的引用（均为演示账号，直接物理删除）
            from sqlalchemy import text as sa_text
            for table, col in [
                ("learning_records", "student_id"),
                ("user_scene_preferences", "user_id"),
                ("course_enrollments", "user_id"),
                ("notes", "owner_id"),
                ("agent_sessions", "user_id"),
                ("notifications", "user_id"),
                ("buddies", "user_id"),
                ("flash_cards", "user_id"),
                ("diagnoses", "user_id"),
                ("resource_favorites", "user_id"),
                ("user_roles", "user_id"),
                ("notification_settings", "user_id"),
                ("learning_plans", "student_id"),
                ("student_evaluations", "student_id"),
            ]:
                await db.execute(
                    sa_text(f"DELETE FROM {table} WHERE {col} = ANY(:ids)"), {"ids": legacy_ids}
                )
            await db.execute(delete(User).where(User.id.in_(legacy_ids)))
        print(f"✓ 清除旧模拟学生: {len(legacy_ids)} 人")

        await db.execute(delete(ContestCourseRequirement).where(ContestCourseRequirement.tenant_id == tenant_id))
        await db.execute(delete(ContestExamNode).where(ContestExamNode.tenant_id == tenant_id))
        await db.execute(delete(ContestMaterial).where(ContestMaterial.tenant_id == tenant_id))
        await db.execute(
            delete(CurriculumOutline).where(
                CurriculumOutline.tenant_id == tenant_id,
                CurriculumOutline.model_name == "contest-import",
            )
        )

        # ---------------- 2. 课程 ----------------
        course = (
            await db.execute(select(Course).where(Course.name == COURSE_NAME))
        ).scalars().first()
        if course is None:
            course = Course(
                tenant_id=tenant_id,
                name=COURSE_NAME,
                code="MATH-G7-CONTEST",
                subject="math",
                grade="七年级",
                semester="2025-2026",
                description="赛题课程：代数式与整式运算 / 方程与方程组 / 不等式与不等式组",
                teacher_id=admin.id,
                is_active=True,
            )
            db.add(course)
            await db.flush()
        print(f"✓ 课程「{COURSE_NAME}」 id={course.id}")

        # ---------------- 3. 学生 D01—D40 ----------------
        student_users: dict[str, User] = {}
        for row in students_csv:
            code = row["学生编号"].strip()
            cls = row["模拟班级编号"].strip()
            email = f"{code.lower()}@student.ai4edu.com"
            user = User(
                tenant_id=tenant_id,
                email=email,
                nickname=f"学生{code}",
                password_hash=hash_password(STUDENT_PASSWORD),
                role="student",
                grade="七年级",
                preferences=json.dumps({"class_code": cls}, ensure_ascii=False),
                default_scene="classroom",
                locale="zh-CN",
                timezone="Asia/Shanghai",
                onboarding_completed=True,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            student_users[code] = user
            db.add(CourseEnrollment(course_id=course.id, user_id=user.id, role="student"))
        print(f"✓ 学生建档 {len(student_users)} 人（DC01/DC02 两班，已选入课程）")

        # ---------------- 4. 课程要求 / 测验节点 / 题目材料 ----------------
        for row in reqs_csv:
            db.add(ContestCourseRequirement(
                tenant_id=tenant_id,
                topic_code=row["主题编号"].strip(),
                topic=row["主题"].strip(),
                topic_goal=row["主题目标"].strip(),
                indicator_code=row["指标编号"].strip(),
                indicator=row["观察指标"].strip(),
                cr_code=row["课标整理编号"].strip() or None,
                cr_pages=row["课标文件页／正文页"].strip() or None,
                textbook_pages=row["教材正文页"].strip() or None,
            ))

        for row in nodes_csv:
            db.add(ContestExamNode(
                tenant_id=tenant_id,
                node_code=row["节点编号"].strip(),
                exam_date=datetime.strptime(row["模拟测验日期"].strip(), "%Y-%m-%d").date()
                if row["模拟测验日期"].strip() else None,
                taught_topics=row["已教及测量主题"].strip() or None,
                note=row["说明"].strip() or None,
                question_codes=row["可用题目编号"].strip().rstrip("、") or None,
            ))

        for row in materials_csv:
            db.add(ContestMaterial(
                tenant_id=tenant_id,
                material_code=row["材料编号"].strip(),
                topic_code=row["主题编号"].strip() or None,
                material_type=row["材料类型"].strip(),
                question_type=row["题型"].strip() or None,
                content=row["题干或内容"].strip() or None,
                options=row["选项"].strip() or None,
                answer=row["参考答案"].strip() or None,
                analysis=row["参考解析"].strip() or None,
                max_score=parse_int(row["满分"]),
                grading_points=row["评分点"].strip() or None,
                indicator_code=row["指标编号"].strip() or None,
                source_file=row["来源或资料文件"].strip() or None,
            ))
        print(f"✓ 课程要求 {len(reqs_csv)} 条 / 测验节点 {len(nodes_csv)} 个 / 题目与材料 {len(materials_csv)} 条")

        # ---------------- 5. 作答记录 → learning_records ----------------
        records = []
        skipped = 0
        for row in answers_csv:
            stu_code = row["学生编号"].strip()
            user = student_users.get(stu_code)
            mat_code = row["材料编号"].strip()
            mat = material_map.get(mat_code)
            if user is None or mat is None:
                skipped += 1
                continue

            ind_code = (mat.get("指标编号") or "").strip()
            indicator_text, topic_code, topic_name = indicator_map.get(
                ind_code, (None, row["主题编号"].strip(), None)
            )
            score = parse_int(row["得分"])
            full = parse_int(row["满分"])
            status = row["评分状态"].strip()
            if status == "已评分" and score is not None and full:
                is_correct = True if score >= full else (False if score == 0 else None)
            else:
                is_correct = None

            records.append(LearningRecord(
                tenant_id=tenant_id,
                student_id=user.id,
                course_id=course.id,
                knowledge_point=indicator_text or topic_name,
                record_type="exam",
                source_ref=row["记录编号"].strip(),
                question_count=1,
                is_correct=is_correct,
                score=float(score) if score is not None else None,
                max_score=float(full) if full is not None else None,
                duration_seconds=None,  # 赛题数据无耗时字段
                recorded_at=parse_dt(row["模拟提交时间"]) or datetime(2026, 1, 20),
                is_simulated=True,
                raw_payload=json.dumps({
                    "record_id": row["记录编号"].strip(),
                    "event_id": row["作答事件编号"].strip(),
                    "revision": parse_int(row["修订版本"]),
                    "submitted_at": row["模拟提交时间"].strip(),
                    "grading_status": status,
                    "final_answer": row["学生最终作答"],
                    "solution_steps": row["解答过程"],
                    "grading_point_scores": row["评分点得分"],
                    "student_code": stu_code,
                    "class_code": class_map.get(stu_code),
                    "material_code": mat_code,
                    "node_code": row["节点编号"].strip(),
                    "topic_code": row["主题编号"].strip(),
                    "indicator_code": (mat.get("指标编号") or "").strip() or None,
                    "question_type": (mat.get("题型") or "").strip() or None,
                    "question_content": (mat.get("题干或内容") or "").strip() or None,
                    "reference_answer": (mat.get("参考答案") or "").strip() or None,
                    "grading_points": (mat.get("评分点") or "").strip() or None,
                }, ensure_ascii=False),
            ))
        for rec in records:
            db.add(rec)
        print(f"✓ 作答记录入库 {len(records)} 条（跳过 {skipped} 条无法关联的记录）")

        # ---------------- 6. 课程梳理大纲（由课程要求直接生成） ----------------
        topics: dict[str, dict] = {}
        for row in reqs_csv:
            t = topics.setdefault(row["主题编号"].strip(), {
                "topic": row["主题"].strip(),
                "goal": row["主题目标"].strip(),
                "textbook": row["教材正文页"].strip(),
                "indicators": [],
            })
            t["indicators"].append(row["观察指标"].strip())

        units = []
        for code, t in topics.items():
            units.append({
                "name": f"{code} {t['topic']}",
                "description": t["goal"],
                "textbook_ref": f"人教版七年级 {t['textbook']}",
                "contents": [
                    {
                        "topic": ind,
                        "description": t["goal"],
                        "requirement": f"掌握：{ind}",
                        "requirement_level": "掌握",
                        "cognitive_level": "apply",
                        "suggested_hours": 2,
                    }
                    for ind in t["indicators"]
                ],
            })
        outline = {
            "course": COURSE_NAME,
            "subject": "math",
            "subject_name": "数学",
            "grade_level": "七年级",
            "scope": "依据《义务教育数学课程标准（2022年版）》与人教版七年级教材，梳理 T01 代数式与整式运算、T02 方程与方程组、T03 不等式与不等式组三个主题的学习内容与要求。",
            "scope_included": [f"{c} {t['topic']}" for c, t in topics.items()],
            "scope_excluded": ["函数与图象", "几何与图形", "统计与概率"],
            "units": units,
            "connections": [
                {"from_topic": "T01 代数式与整式运算", "to_topic": "T02 方程与方程组",
                 "link_type": "prerequisite", "description": "代数式表示与整式运算是列方程、解方程的基础。"},
                {"from_topic": "T02 方程与方程组", "to_topic": "T03 不等式与不等式组",
                 "link_type": "related", "description": "一元一次不等式的解法可类比一元一次方程，注意除以负数变号。"},
            ],
            "sources": [
                {"title": "义务教育数学课程标准（2022年版）", "publisher": "中华人民共和国教育部",
                 "url": "contest/课程标准_2022.pdf", "source_type": "curriculum_standard",
                 "usage": "三个主题的课标条目出处（CR01—CR03）"},
                {"title": "人教版七年级数学教材切片 B01—B08", "publisher": "人民教育出版社",
                 "url": "contest/", "source_type": "textbook",
                 "usage": "主题对应的教材正文切片（上册68—109、下册相关页）"},
            ],
        }
        db.add(CurriculumOutline(
            tenant_id=tenant_id,
            user_id=admin.id,
            course_query="初中数学七年级（代数式与整式运算、方程与方程组、不等式与不等式组）",
            subject="math",
            grade_level="七年级",
            scope_hint="赛题指定三主题",
            title="七年级数学三主题课程梳理（赛题版）",
            outline=json.dumps(outline, ensure_ascii=False),
            sources_json=json.dumps(outline["sources"], ensure_ascii=False),
            model_name="contest-import",
            used_web_search=False,
            status="completed",
        ))
        print("✓ 课程梳理大纲已生成（课程梳理页可见）")

        await db.commit()

    # ---------------- 7. PDF 资源 → MinIO + resources 表 ----------------
    uploaded, missing = await upload_pdfs(data_dir, admin_id=admin.id, course_id=course.id,
                                          tenant_id=tenant_id)
    print(f"✓ PDF 资源: 上传 {uploaded} 个" + (f"，缺失 {missing} 个（跳过）" if missing else ""))

    print("\n=== 导入完成 ===")


async def upload_pdfs(data_dir: Path, admin_id: int, course_id: int, tenant_id: int) -> tuple[int, int]:
    """PDF 上传 MinIO 并登记 resources 表（RAG 向量索引需有效 Embedding Key，另行开启）"""
    from minio import Minio

    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )
    bucket = settings.MINIO_BUCKET
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    uploaded = missing = 0
    async with async_session_factory() as db:
        for filename, title, kind, code in PDF_FILES:
            path = data_dir / filename
            if not path.exists():
                missing += 1
                print(f"  ⚠ 缺少文件: {filename}")
                continue
            key = f"contest/{filename}"
            client.fput_object(bucket, key, str(path), content_type="application/pdf")

            exists = (
                await db.execute(select(Resource).where(Resource.file_key == key))
            ).scalars().first()
            if exists is None:
                db.add(Resource(
                    tenant_id=tenant_id,
                    title=title,
                    description=f"赛题资料（{'课程标准' if kind == 'curriculum_standard' else '教材切片'}）",
                    resource_type="pdf",
                    mime_type="application/pdf",
                    file_size=path.stat().st_size,
                    file_key=key,
                    course_id=course_id,
                    uploader_id=admin_id,
                    tags=json.dumps(["赛事资料", "七年级数学"], ensure_ascii=False),
                    metadata_json=json.dumps({"material_code": code, "kind": kind}, ensure_ascii=False),
                    is_public=False,
                    is_active=True,
                ))
            uploaded += 1
        await db.commit()
    return uploaded, missing


if __name__ == "__main__":
    asyncio.run(main())
