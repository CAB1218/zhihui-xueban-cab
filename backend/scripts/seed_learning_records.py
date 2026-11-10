"""
AI4Edu 模拟学情数据生成脚本
任务2：学情分析 —— 生成带「缺失 / 异常 / 重复」三类质量问题的模拟学情记录

数据是刻意"脏"的：真实校园系统采上来的数据往往就是这样。
质量检查与清洗留给分析服务处理，这样成果里才能说清楚「怎么发现的、怎么处理的」。
"""
import asyncio
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete, select

from app.core.security import hash_password
from app.database import async_session_factory
from app.models.course import Course
from app.models.learning_record import LearningRecord
from app.models.tenant import Tenant
from app.models.user import User

# ---------------------------------------------------------------------------
# 学生画像：base = 该课程的基础正确率；bias = 个别知识点的能力偏移（+强 / -弱）
# 刻意设计出「学霸 / 偏科 / 后进 / 少样本」几类人，便于后面讲个体差异
# ---------------------------------------------------------------------------
STUDENT_PROFILES = [
    # (邮箱前缀, 昵称, 基础正确率, 知识点偏移, 每点作答次数范围)
    ("chenjiahe", "陈嘉禾", 0.92, {}, (4, 6)),
    ("lisiyuan", "李思远", 0.78, {}, (3, 5)),
    ("wangyutong", "王雨桐", 0.72, {"树与二叉树": 0.25, "排序": -0.40}, (4, 6)),
    ("zhanghaoran", "张浩然", 0.68, {"图的遍历": -0.20}, (3, 5)),
    ("liuxinran", "刘欣然", 0.85, {"图的遍历": 0.10}, (4, 5)),
    ("zhaozimo", "赵子墨", 0.55, {"排序": -0.15}, (3, 5)),
    ("sunyue", "孙悦", 0.42, {}, (3, 5)),
    ("zhoujingxing", "周景行", 0.75, {"查找": 0.15}, (3, 4)),
    ("wusitong", "吴思彤", 0.80, {}, (3, 4)),
    # 少样本学生：只有 4 条记录，用来演示「证据不足 ≠ 未掌握」
    ("zhengke", "郑可", 0.70, {}, (1, 1)),
]

# 知识点：(名称, 群体难度偏移) —— 负数表示这门课普遍偏弱，用于构造「共性薄弱点」
KP_CS = [
    ("线性表", 0.08),
    ("栈与队列", 0.04),
    ("串与数组", 0.00),
    ("树与二叉树", -0.10),
    ("图的遍历", -0.26),   # 群体共性薄弱
    ("排序", -0.22),       # 群体共性薄弱
    ("查找", -0.04),
    ("哈希表", -0.08),
]

KP_MATH = [
    ("极限与连续", 0.06),
    ("导数与微分", 0.02),
    ("微分中值定理", -0.24),  # 群体共性薄弱
    ("不定积分", -0.06),
    ("定积分", -0.12),
    ("无穷级数", -0.28),      # 群体共性薄弱
]

RECORD_TYPES = ["quiz", "homework", "exam", "classroom", "self_test"]
TYPE_WEIGHTS = [0.42, 0.24, 0.10, 0.14, 0.10]

BASE_TIME = datetime(2026, 11, 8, 20, 0, 0)


def pick(vals, weights=None):
    return random.choices(vals, weights=weights, k=1)[0]


async def main() -> None:
    random.seed(20261110)  # 固定随机种子，保证可复现

    async with async_session_factory() as db:
        tenant = (await db.execute(select(Tenant).order_by(Tenant.id))).scalars().first()
        if tenant is None:
            print("✗ 未找到租户，请先执行 seed_data.py")
            return
        tenant_id = tenant.id

        courses = {
            c.name: c for c in (await db.execute(select(Course))).scalars().all()
        }
        cs_course = courses.get("数据结构")
        math_course = courses.get("高等数学（上）")
        if cs_course is None or math_course is None:
            print(f"✗ 缺少课程，现有：{list(courses)}")
            return

        # ---------------- 1. 建模拟学生 ----------------
        students = []
        for prefix, nickname, base, bias, rng in STUDENT_PROFILES:
            email = f"{prefix}@student.ai4edu.com"
            user = (
                await db.execute(select(User).where(User.email == email))
            ).scalars().first()
            if user is None:
                user = User(
                    tenant_id=tenant_id,
                    email=email,
                    nickname=nickname,
                    password_hash=hash_password("student123"),
                    role="student",
                    grade="大二",
                    major="计算机科学与技术",
                    default_scene="classroom",
                    locale="zh-CN",
                    timezone="Asia/Shanghai",
                    onboarding_completed=True,
                    is_active=True,
                )
                db.add(user)
                await db.flush()
            students.append(
                {
                    "user": user,
                    "base": base,
                    "bias": bias,
                    "rng": rng,
                }
            )

        # ---------------- 2. 清空旧的模拟记录 ----------------
        await db.execute(
            delete(LearningRecord).where(LearningRecord.is_simulated.is_(True))
        )

        # ---------------- 3. 生成作答记录 ----------------
        records = []
        for st in students:
            user = st["user"]

            # 数据结构：全体学生都做
            for kp, kp_offset in KP_CS:
                lo, hi = st["rng"]
                n = random.randint(lo, hi)
                p = st["base"] + kp_offset + st["bias"].get(kp, 0.0)
                p = max(0.05, min(0.97, p))
                for _ in range(n):
                    records.append(make_record(user.id, cs_course.id, kp, p, tenant_id))

            # 高数：只给前 6 个学生（模拟选课不同），让"多课程"更真实
            if st["base"] >= 0.68:
                for kp, kp_offset in KP_MATH:
                    p = st["base"] + kp_offset + st["bias"].get(kp, 0.0)
                    p = max(0.05, min(0.97, p))
                    for _ in range(random.randint(2, 4)):
                        records.append(make_record(user.id, math_course.id, kp, p, tenant_id))

        # 验收学生也留一点真实记录（少一些，避免抢戏）
        test_user = (
            await db.execute(select(User).where(User.email == "student_test@ai4edu.com"))
        ).scalars().first()
        if test_user:
            for kp, kp_offset in KP_CS[:5]:
                p = max(0.05, min(0.95, 0.70 + kp_offset))
                for _ in range(random.randint(2, 3)):
                    records.append(make_record(test_user.id, cs_course.id, kp, p, tenant_id))

        clean_count = len(records)

        # ---------------- 4. 注入质量问题 ----------------
        issues = inject_quality_issues(records)

        # ---------------- 5. 落库 ----------------
        for r in records:
            db.add(LearningRecord(**r))
        await db.commit()

        print(f"✓ 模拟学生 {len(students)} 人 + 验收学生 1 人")
        print(f"✓ 原始记录 {len(records)} 条（其中干净记录 {clean_count} 条）")
        print("✓ 注入质量问题：")
        for k, v in issues.items():
            print(f"    - {k}: {v} 条")


def make_record(student_id: int, course_id: int, kp: str, p_correct: float, tenant_id: int) -> dict:
    """按给定正确率生成一条作答记录"""
    correct = random.random() < p_correct
    qcount = random.choice([1, 1, 1, 5, 10])
    max_score = float(qcount * 10)
    # 得分围绕正确率波动
    ratio = 1.0 if correct else random.uniform(0.0, 0.4)
    if qcount > 1:
        ratio = min(1.0, max(0.0, p_correct * 2 - 1 + random.uniform(-0.35, 0.35)))
    score = round(max_score * ratio, 1)

    days_ago = random.randint(0, 55)
    minutes = random.randint(0, 600)
    recorded = BASE_TIME - timedelta(days=days_ago, minutes=minutes)

    rtype = pick(RECORD_TYPES, TYPE_WEIGHTS)
    # 耗时：正常 40s ~ 40min，随题量放大
    if rtype == "exam":
        duration = random.randint(1200, 3600)
    elif qcount >= 10:
        duration = random.randint(300, 1500)
    else:
        duration = random.randint(40, 600)

    return {
        "tenant_id": tenant_id,
        "student_id": student_id,
        "course_id": course_id,
        "knowledge_point": kp,
        "record_type": rtype,
        "source_ref": f"{rtype.upper()}-{recorded.strftime('%Y%m%d')}-{random.randint(100, 999)}",
        "question_count": qcount,
        "is_correct": correct,
        "score": score,
        "max_score": max_score,
        "duration_seconds": duration,
        "recorded_at": recorded,
        "is_simulated": True,
        "raw_payload": json.dumps(
            {"kp": kp, "p": round(p_correct, 3), "q": qcount, "src": "seed_simulated"},
            ensure_ascii=False,
        ),
        "created_at": datetime.utcnow(),
    }


def inject_quality_issues(records: list) -> dict:
    """刻意注入缺失、异常、重复三类问题，返回各类问题条数"""
    idx = list(range(len(records)))
    random.shuffle(idx)

    counts = {}
    cursor = 0

    def take(n: int):
        nonlocal cursor
        picked = idx[cursor: cursor + n]
        cursor += n
        return picked

    # --- 缺失：分值缺失（但仍有对错，可据对错辅助判断） ---
    for i in take(8):
        records[i]["score"] = None
        counts["score 缺失（有对错标记）"] = counts.get("score 缺失（有对错标记）", 0) + 1

    # --- 缺失：分值和对错同时缺失（这条记录实质上无法判断掌握情况） ---
    for i in take(7):
        records[i]["score"] = None
        records[i]["is_correct"] = None
        counts["score 与对错同时缺失"] = counts.get("score 与对错同时缺失", 0) + 1

    # --- 缺失：知识点为空 ---
    for i in take(10):
        records[i]["knowledge_point"] = None
        counts["知识点缺失"] = counts.get("知识点缺失", 0) + 1

    # --- 缺失：耗时为空 ---
    for i in take(5):
        records[i]["duration_seconds"] = None
        counts["耗时缺失"] = counts.get("耗时缺失", 0) + 1

    # --- 异常：分数超过满分 ---
    for i in take(5):
        ms = records[i]["max_score"] or 10.0
        records[i]["score"] = round(ms + random.choice([5.0, 8.5, 10.0]), 1)
        records[i]["max_score"] = ms
        counts["分数超过满分"] = counts.get("分数超过满分", 0) + 1

    # --- 异常：耗时离谱（跨天、明显非真实作答） ---
    for i in take(6):
        records[i]["duration_seconds"] = random.choice([86400, 99999, 360000, 999999])
        counts["耗时异常（超过 6 小时）"] = counts.get("耗时异常（超过 6 小时）", 0) + 1

    # --- 异常：负耗时 ---
    for i in take(3):
        records[i]["duration_seconds"] = random.choice([-30, -120, -5])
        counts["耗时为负"] = counts.get("耗时为负", 0) + 1

    # --- 异常：记录时间在未来（设备时间错乱） ---
    for i in take(2):
        records[i]["recorded_at"] = datetime(2027, 3, random.randint(1, 28), 10, 0, 0)
        counts["记录时间在未来"] = counts.get("记录时间在未来", 0) + 1

    # --- 重复：完全重复（除 id 外全同，模拟重复上报） ---
    dup_src = take(16)
    for i in dup_src:
        clone = dict(records[i])
        clone["raw_payload"] = json.dumps(
            {"dup_of": "seed", "note": "重复上报的同一份记录"}, ensure_ascii=False
        )
        records.append(clone)
    counts["完全重复记录"] = len(dup_src)

    # --- 重复：同学生 + 同知识点 + 同时间，但分数不同（像重考/二次提交） ---
    near_dup = take(5)
    for i in near_dup:
        clone = dict(records[i])
        if clone.get("score") is not None and clone.get("max_score"):
            clone["score"] = round(clone["max_score"] * random.uniform(0.5, 1.0), 1)
        clone["is_correct"] = not bool(records[i].get("is_correct"))
        clone["raw_payload"] = json.dumps(
            {"dup_of": "seed", "note": "同一时段二次提交"}, ensure_ascii=False
        )
        records.append(clone)
    counts["同人同知识点同时段的重复提交"] = len(near_dup)

    return counts


if __name__ == "__main__":
    asyncio.run(main())
