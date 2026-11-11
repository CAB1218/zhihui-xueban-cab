"""
AI4EDU 文件导入服务

支撑两个入口：
- 课程梳理：导入课表 / 大纲文件（csv / xlsx / txt / md / json），解析为梳理大纲
- 学情分析：导入成绩 / 答题记录（csv / xlsx），逐行校验后写入 learning_records

设计原则：
- 逐行校验、逐行报错，坏行不拖垮整个文件
- 列名支持中文与英文别名，兼容学校常见导出的表头写法
- 导入的记录如实标注 is_simulated=False（真实导入数据，与演示用的模拟数据区分）
"""
import csv
import io
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.core.exceptions import AppException

MAX_FILE_BYTES = 5 * 1024 * 1024  # 5MB
MAX_RECORD_ROWS = 5000
MAX_CURRICULUM_ROWS = 1000


# ---------------------------------------------------------------------------
# 通用：文件读取
# ---------------------------------------------------------------------------

def _decode_text(data: bytes) -> str:
    """按常见编码解码文本（utf-8 / utf-8-sig / gbk）"""
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise AppException(code=400, message="文件编码无法识别，请使用 UTF-8 或 GBK 编码的文本文件")


def read_table(data: bytes, filename: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """把 csv / xlsx 读成 (表头, 行字典列表)，单元格一律转字符串并去首尾空白"""
    name = (filename or "").lower()
    if name.endswith(".xlsx"):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:  # pragma: no cover
            raise AppException(code=500, message="服务器未安装 openpyxl，无法解析 xlsx 文件") from exc
        try:
            wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        except Exception as exc:  # noqa: BLE001
            raise AppException(code=400, message=f"xlsx 文件解析失败：{str(exc)[:120]}")
        ws = wb.worksheets[0]
        rows_raw = [list(r) for r in ws.iter_rows(values_only=True)]
        wb.close()
        if not rows_raw:
            raise AppException(code=400, message="表格为空")
        headers = [str(h).strip() if h is not None else "" for h in rows_raw[0]]
        rows: List[Dict[str, str]] = []
        for r in rows_raw[1:]:
            row = {
                headers[i]: (str(v).strip() if v is not None else "")
                for i, v in enumerate(r) if i < len(headers) and headers[i]
            }
            if any(v for v in row.values()):
                rows.append(row)
        return headers, rows

    if name.endswith(".csv") or name.endswith(".txt"):
        text = _decode_text(data)
        reader = csv.reader(io.StringIO(text))
        rows_raw = [r for r in reader if any((cell or "").strip() for cell in r)]
        if not rows_raw:
            raise AppException(code=400, message="表格为空")
        headers = [h.strip() for h in rows_raw[0]]
        rows = []
        for r in rows_raw[1:]:
            row = {headers[i]: r[i].strip() for i in range(min(len(headers), len(r))) if headers[i]}
            rows.append(row)
        return headers, rows

    raise AppException(code=400, message="仅支持 .csv / .xlsx 表格文件")


def _pick(row: Dict[str, str], *aliases: str) -> str:
    """按别名优先级取列值（忽略大小写与括号全半角差异）"""
    norm = {re.sub(r"[\s（）()]+", "", k).lower(): v for k, v in row.items()}
    for a in aliases:
        key = re.sub(r"[\s（）()]+", "", a).lower()
        if key in norm and norm[key] != "":
            return norm[key]
    return ""


# ---------------------------------------------------------------------------
# 学情记录解析
# ---------------------------------------------------------------------------

_RECORD_TYPE_MAP = {
    "quiz": "quiz", "测验": "quiz", "测试": "quiz", "练习": "quiz",
    "homework": "homework", "作业": "homework",
    "exam": "exam", "考试": "exam",
    "classroom": "classroom", "课堂": "classroom", "课堂互动": "classroom",
    "self_test": "self_test", "自测": "self_test", "自学": "self_test",
}

_TRUE_WORDS = {"对", "正确", "是", "true", "t", "yes", "y", "1", "√", "✓", "对勾"}
_FALSE_WORDS = {"错", "错误", "否", "false", "f", "no", "n", "0", "×", "x", "叉"}

_STUDENT_COLS = ("学生id", "student_id", "学号", "学生姓名", "姓名", "学生")
_COURSE_COLS = ("课程id", "course_id", "课程", "课程名称", "科目")

_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d",
    "%Y.%m.%d %H:%M", "%Y.%m.%d",
)


def parse_datetime(text: str) -> Optional[datetime]:
    """解析常见日期时间格式；解析失败返回 None"""
    text = (text or "").strip()
    if not text:
        return None
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        # ISO 8601（含 T 与毫秒）
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _parse_float(text: str) -> Tuple[Optional[float], bool]:
    """返回 (值, 是否非空但解析失败)"""
    text = (text or "").strip().rstrip("分")
    if not text:
        return None, False
    try:
        return float(text), False
    except ValueError:
        return None, True


def _parse_int(text: str) -> Tuple[Optional[int], bool]:
    text = (text or "").strip().rstrip("秒")
    if not text:
        return None, False
    try:
        return int(float(text)), False
    except ValueError:
        return None, True


def _parse_correct(text: str) -> Optional[bool]:
    t = (text or "").strip().lower()
    if not text.strip():
        return None
    if t in _TRUE_WORDS:
        return True
    if t in _FALSE_WORDS:
        return False
    return None


def parse_learning_record_rows(
    data: bytes,
    filename: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """解析成绩/答题记录文件 → (待入库行, 失败行明细)

    每行产出字典：student_key / course_key / knowledge_point / record_type /
    is_correct / score / max_score / duration_seconds / question_count /
    recorded_at / source_ref / raw（原始行 JSON，用于溯源）
    """
    headers, rows = read_table(data, filename)
    if len(rows) > MAX_RECORD_ROWS:
        raise AppException(code=400, message=f"一次最多导入 {MAX_RECORD_ROWS} 行，当前文件有 {len(rows)} 行")
    if not rows:
        raise AppException(code=400, message="文件中没有数据行")

    ok: List[Dict[str, Any]] = []
    bad: List[Dict[str, Any]] = []

    for idx, row in enumerate(rows, start=2):  # start=2：第 1 行是表头
        errors: List[str] = []
        student_key = _pick(row, *_STUDENT_COLS)
        course_key = _pick(row, *_COURSE_COLS)
        knowledge_point = _pick(row, "知识点", "knowledge_point", "kp", "主题", "考点")
        record_type_raw = _pick(row, "记录类型", "record_type", "类型")
        correct_raw = _pick(row, "对错", "是否正确", "is_correct", "结果", "正误")
        score_raw = _pick(row, "得分", "score", "分数", "成绩")
        max_score_raw = _pick(row, "满分", "max_score", "总分")
        duration_raw = _pick(row, "耗时秒", "耗时", "duration_seconds", "时长")
        qcount_raw = _pick(row, "题目数", "题数", "question_count")
        time_raw = _pick(row, "记录时间", "时间", "日期", "recorded_at", "作答时间")
        source_ref = _pick(row, "来源", "source_ref", "试卷", "备注")[:120]

        if not student_key:
            errors.append("缺少学生列（学生姓名/学号）")

        score, score_bad = _parse_float(score_raw)
        if score_bad:
            errors.append(f"得分「{score_raw}」不是数字")
        max_score, max_bad = _parse_float(max_score_raw)
        if max_bad:
            errors.append(f"满分「{max_score_raw}」不是数字")
        duration, dur_bad = _parse_int(duration_raw)
        if dur_bad:
            errors.append(f"耗时「{duration_raw}」不是数字")
        qcount, qc_bad = _parse_int(qcount_raw)
        if qc_bad:
            errors.append(f"题目数「{qcount_raw}」不是整数")

        recorded_at = parse_datetime(time_raw)
        if time_raw and recorded_at is None:
            errors.append(f"时间「{time_raw}」无法识别（支持 2026-01-01 08:30 这类格式）")

        record_type = _RECORD_TYPE_MAP.get(record_type_raw.strip().lower(), "quiz") \
            if record_type_raw else "quiz"

        # 至少要有「可判断掌握程度」的一种依据：对错 / 得分 / 知识点
        if correct_raw == "" and score is None and not knowledge_point:
            errors.append("该行没有对错、得分或知识点中的任何一项，无法用于学情分析")

        if errors:
            bad.append({"row": idx, "reasons": errors, "raw": {k: v for k, v in row.items() if v}})
            continue

        ok.append(
            {
                "row_no": idx,
                "student_key": student_key,
                "course_key": course_key,
                "knowledge_point": knowledge_point[:120] or None,
                "record_type": record_type,
                "is_correct": _parse_correct(correct_raw),
                "score": score,
                "max_score": max_score,
                "duration_seconds": duration,
                "question_count": qcount,
                "recorded_at": recorded_at or datetime.now(),
                "source_ref": source_ref or None,
                "raw": json.dumps({"row": idx, **{k: v for k, v in row.items() if v}}, ensure_ascii=False),
            }
        )

    return ok, bad


# ---------------------------------------------------------------------------
# 课表 / 课程大纲解析
# ---------------------------------------------------------------------------

def parse_curriculum_table(data: bytes, filename: str) -> Dict[str, Any]:
    """解析课表/大纲表格 → 大纲骨架字典

    支持的列（中文/英文别名）：
      课程名称、学科、学段年级、单元（章节）、学习内容、内容说明、
      要求、要求水平、认知水平、建议课时、教材出处
    """
    headers, rows = read_table(data, filename)
    if len(rows) > MAX_CURRICULUM_ROWS:
        raise AppException(code=400, message=f"一次最多导入 {MAX_CURRICULUM_ROWS} 行")
    if not rows:
        raise AppException(code=400, message="文件中没有数据行")

    unit_col_present = any(
        _pick(r, "单元", "章节", "unit", "章") for r in rows
    )
    topic_col_present = any(
        _pick(r, "学习内容", "内容", "topic", "主题", "知识点") for r in rows
    )
    if not (unit_col_present or topic_col_present):
        raise AppException(
            code=400,
            message="未识别到「单元/章节」或「学习内容」列。课表类文件请包含课程的知识点/章节结构；"
                    "可先下载导入模板，按模板列整理后再上传。",
        )

    course = _pick(rows[0], "课程名称", "课程", "course", "课程名")
    if not course:
        stem = re.sub(r"\.(csv|xlsx|txt|md)$", "", filename or "", flags=re.IGNORECASE).strip()
        course = stem or "导入课程"
    subject_text = _pick(rows[0], "学科", "subject")
    grade = _pick(rows[0], "学段年级", "年级", "学段", "grade_level", "grade")
    textbook = _pick(rows[0], "教材", "教材出处", "textbook_ref", "教材版本")

    units: List[Dict[str, Any]] = []
    unit_map: Dict[str, Dict[str, Any]] = {}
    skipped_rows = 0

    for row in rows:
        unit_name = _pick(row, "单元", "章节", "unit", "章") or "未分组内容"
        topic = _pick(row, "学习内容", "内容", "topic", "主题", "知识点")
        if not topic:
            skipped_rows += 1
            continue
        if unit_name not in unit_map:
            unit_map[unit_name] = {
                "name": unit_name,
                "description": "",
                "textbook_ref": textbook,
                "contents": [],
            }
            units.append(unit_map[unit_name])
        hours_raw = _pick(row, "建议课时", "课时", "suggested_hours")
        hours, _ = _parse_float(hours_raw)
        unit_map[unit_name]["contents"].append(
            {
                "topic": topic[:120],
                "description": _pick(row, "内容说明", "说明", "description")[:300],
                "requirement": _pick(row, "要求", "requirement"),
                "requirement_level": _pick(row, "要求水平", "requirement_level") or "理解",
                "cognitive_level": _normalize_cognitive(_pick(row, "认知水平", "cognitive_level")),
                "suggested_hours": hours,
            }
        )

    if not units:
        raise AppException(code=400, message="表格中没有可识别的学习内容行")

    return {
        "course": course[:200],
        "subject_hint": subject_text,
        "grade_level": grade[:50],
        "textbook_ref": textbook,
        "units": units,
        "skipped_rows": skipped_rows,
    }


def _normalize_cognitive(text: str) -> str:
    mapping = {
        "记忆": "remember", "remember": "remember",
        "理解": "understand", "understand": "understand",
        "运用": "apply", "应用": "apply", "apply": "apply",
        "分析": "analyze", "analyze": "analyze",
        "评价": "evaluate", "evaluate": "evaluate",
        "创造": "create", "create": "create",
    }
    return mapping.get((text or "").strip().lower(), "understand")


_UNIT_LINE = re.compile(r"^(?:#{1,4}\s*)?(第\s*[0-9一二三四五六七八九十百]+\s*[章节单元模块篇部]\s*[:：、.]?\s*.+|[一二三四五六七八九十]+[、.]\s*.+)$")
_TOPIC_LINE = re.compile(r"^[-*•\d]+[.、)）]?\s*(.+)$")
_GRADE_HINT = re.compile(r"(七年级|八年级|九年级|初一|初二|初三|高一|高二|高三|大一|大二|大三|大四|小学|初中|高中|大学)")


def parse_curriculum_text(data: bytes, filename: str) -> Dict[str, Any]:
    """解析 txt / md 大纲文本 → 大纲骨架

    规则：
    - 第一处 `#` 标题或首行作为课程名
    - 「第X章/第X单元/一、」开头的行视为单元
    - `-`/`*` 开头的行作为当前单元下的学习内容
    """
    text = _decode_text(data)
    lines = [ln.rstrip() for ln in text.splitlines()]

    course = ""
    units: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    grade = ""

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if not grade:
            m = _GRADE_HINT.search(line)
            if m:
                grade = m.group(1)

        heading = re.match(r"^(#{1,6})\s*(.+)$", line)
        if heading and not course:
            course = heading.group(2).strip()
            continue

        m_unit = _UNIT_LINE.match(line)
        if m_unit:
            name = re.sub(r"^#{1,4}\s*", "", m_unit.group(1)).strip()
            current = {"name": name[:80], "description": "", "textbook_ref": "", "contents": []}
            units.append(current)
            continue

        m_topic = _TOPIC_LINE.match(line)
        if m_topic and current is not None and not heading:
            topic = m_topic.group(1).strip()
            if topic:
                current["contents"].append(
                    {
                        "topic": topic[:120],
                        "description": "",
                        "requirement": "",
                        "requirement_level": "理解",
                        "cognitive_level": "understand",
                        "suggested_hours": None,
                    }
                )
            continue

        if not course:
            course = line[:200]

    if not course:
        stem = re.sub(r"\.(txt|md)$", "", filename or "", flags=re.IGNORECASE).strip()
        course = stem or "导入课程"

    if not units:
        # 没有章节结构时，把全部非空行作为一门课程的扁平内容
        contents = [
            {
                "topic": ln.strip()[:120],
                "description": "",
                "requirement": "",
                "requirement_level": "了解",
                "cognitive_level": "understand",
                "suggested_hours": None,
            }
            for ln in lines
            if ln.strip() and not ln.strip().startswith("#")
        ][:200]
        if len(contents) < 2:
            raise AppException(
                code=400,
                message="文本内容太少或没有可识别的章节结构。可使用「第X章 标题」划分单元，"
                        "单元下用「- 学习内容」列出条目；也可下载模板按表格整理。",
            )
        units = [{"name": "课程目录", "description": "", "textbook_ref": "", "contents": contents}]

    return {
        "course": course[:200],
        "subject_hint": "",
        "grade_level": grade[:50],
        "textbook_ref": "",
        "units": units,
        "skipped_rows": 0,
    }


def parse_curriculum_json(data: bytes, filename: str) -> Dict[str, Any]:
    """解析课程梳理 JSON（支持本系统导出的 outline json）"""
    text = _decode_text(data)
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AppException(code=400, message=f"JSON 解析失败：{exc}")

    if isinstance(raw, dict) and "outline" in raw and isinstance(raw["outline"], (dict, str)):
        outline = raw["outline"]
        if isinstance(outline, str):
            outline = json.loads(outline)
        raw = outline
    if not isinstance(raw, dict) or not raw.get("units"):
        raise AppException(code=400, message="JSON 中没有可识别的大纲结构（缺少 units）")
    if not raw.get("course"):
        raw["course"] = re.sub(r"\.json$", "", filename or "", flags=re.IGNORECASE) or "导入课程"
    return {"outline": raw}


# ---------------------------------------------------------------------------
# 个人课表解析（场景仪表盘「导入课表」）
# ---------------------------------------------------------------------------

MAX_SCHEDULE_ROWS = 500

# 星期别名：数字 / 中文 / 英文缩写都接受
_WEEKDAY_MAP = {
    "1": 1, "一": 1, "周一": 1, "星期一": 1, "礼拜一": 1, "mon": 1, "monday": 1,
    "2": 2, "二": 2, "周二": 2, "星期二": 2, "礼拜二": 2, "tue": 2, "tuesday": 2,
    "3": 3, "三": 3, "周三": 3, "星期三": 3, "礼拜三": 3, "wed": 3, "wednesday": 3,
    "4": 4, "四": 4, "周四": 4, "星期四": 4, "礼拜四": 4, "thu": 4, "thursday": 4,
    "5": 5, "五": 5, "周五": 5, "星期五": 5, "礼拜五": 5, "fri": 5, "friday": 5,
    "6": 6, "六": 6, "周六": 6, "星期六": 6, "礼拜六": 6, "sat": 6, "saturday": 6,
    "7": 7, "日": 7, "天": 7, "周日": 7, "周天": 7, "星期日": 7, "星期天": 7,
    "礼拜日": 7, "sun": 7, "sunday": 7,
}

_TIME_RANGE = re.compile(r"(\d{1,2}\s*[:：]?\s*\d{0,2})\s*[-~～—至到]\s*(\d{1,2}\s*[:：]?\s*\d{0,2})")


def parse_weekday(text: str) -> Optional[int]:
    """把「周一 / 星期一 / 礼拜一 / 1 / Mon」统一成 1-7"""
    key = re.sub(r"[\s.。]+", "", (text or "").strip()).lower()
    key = key.replace("星期", "周").replace("礼拜", "周")  # 星期X / 礼拜X 统一成 周X
    if not key:
        return None
    if key in _WEEKDAY_MAP:
        return _WEEKDAY_MAP[key]
    # 兼容「周一上午」「星期一第1-2节」这类附带说明的写法
    for alias, num in _WEEKDAY_MAP.items():
        if len(alias) >= 2 and key.startswith(alias):
            return num
    return None


def parse_hhmm(text: str) -> Optional[str]:
    """把 8 / 8:00 / 08：00 / 0800 / 8点 / 8点30 / 08:00:00 统一成 'HH:mm'"""
    raw = re.sub(r"\s+", "", (text or "").strip())
    if not raw:
        return None
    raw = raw.replace("：", ":").replace("点", ":").replace("时", ":")
    if raw.endswith("分"):
        raw = raw[:-1]
    raw = raw.strip(":")  # 「8点」「8时」替换后是 "8:"，去掉尾冒号按纯数字处理
    # 纯数字：8 / 800 / 0800 / 0830
    if re.fullmatch(r"\d{1,4}", raw):
        if len(raw) <= 2:
            hour, minute = int(raw), 0
        else:
            hour, minute = int(raw[:-2]), int(raw[-2:])
        return _fmt_hhmm(hour, minute)
    m = re.fullmatch(r"(\d{1,2}):(\d{1,2})(?::\d{1,2})?", raw)
    if m:
        return _fmt_hhmm(int(m.group(1)), int(m.group(2)))
    return None


def _fmt_hhmm(hour: int, minute: int) -> Optional[str]:
    if 0 <= hour <= 23 and 0 <= minute <= 59:
        return f"{hour:02d}:{minute:02d}"
    return None


def split_time_range(text: str) -> Tuple[str, str]:
    """从「08:00-09:40」「8:00~9:40」这类单元格里拆出起止时间；拆不出返回空串"""
    m = _TIME_RANGE.search((text or "").replace("：", ":"))
    if not m:
        return "", ""
    return m.group(1).strip(), m.group(2).strip()


def parse_schedule_rows(data: bytes, filename: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    解析个人课表文件（csv / xlsx），逐行校验

    必需列：课程名称、星期、开始时间、结束时间
    可选列：上课地点、任课教师、周次、备注

    返回 (通过行, 失败行)；失败行带行号与原因，不阻断其它行导入。
    """
    headers, rows = read_table(data, filename)
    if not rows:
        raise AppException(code=400, message="表格里没有数据行，请确认第一行是表头、第二行起是课程")
    if len(rows) > MAX_SCHEDULE_ROWS:
        raise AppException(code=400, message=f"单次最多导入 {MAX_SCHEDULE_ROWS} 条课表记录，当前 {len(rows)} 条")

    ok: List[Dict[str, Any]] = []
    bad: List[Dict[str, Any]] = []
    seen: Dict[Tuple[int, str, str], int] = {}

    for idx, row in enumerate(rows, start=2):  # 第 1 行是表头
        name = _pick(row, "课程名称", "课程", "科目", "课程名", "名称", "course", "course_name", "name").strip()
        weekday_raw = _pick(row, "星期", "周几", "星期几", "上课日", "weekday", "day", "week")
        start_raw = _pick(row, "开始时间", "开始", "上课时间", "start", "start_time", "起")
        end_raw = _pick(row, "结束时间", "结束", "下课时间", "end", "end_time", "止")
        location = _pick(row, "上课地点", "地点", "教室", "location", "room", "classroom", "place")
        teacher = _pick(row, "任课教师", "教师", "老师", "teacher", "instructor")
        weeks = _pick(row, "周次", "上课周", "周数", "weeks", "week_range")
        note = _pick(row, "备注", "note", "remark", "comment")
        # 有些表把上课时间写成一列「08:00-09:40」，任意一列能拆出区间就按区间走
        for candidate in (start_raw, end_raw, _pick(row, "上课时间", "时间段", "时间", "time", "period")):
            range_start, range_end = split_time_range(candidate)
            if range_start and range_end:
                start_raw, end_raw = range_start, range_end
                break

        reasons: List[str] = []
        if not name:
            reasons.append("缺少课程名称")
        weekday = parse_weekday(weekday_raw)
        if weekday is None:
            reasons.append(
                f"星期无法识别：{weekday_raw or '空'}（可填 周一~周日、星期一~星期日、1~7 或 Mon~Sun）"
            )
        start = parse_hhmm(start_raw)
        end = parse_hhmm(end_raw)
        if start is None:
            reasons.append(
                f"开始时间无法识别：{start_raw or '空'}（可填 08:00、8:00、0800、8点）"
            )
        if end is None:
            reasons.append(
                f"结束时间无法识别：{end_raw or '空'}（可填 09:40、9:40、0940、9点40）"
            )
        if start and end and start >= end:
            reasons.append(f"结束时间不晚于开始时间（{start} → {end}）")

        if reasons:
            bad.append({"row": idx, "reasons": reasons, "raw": row})
            continue

        dup_key = (weekday, name, start)
        if dup_key in seen:
            bad.append(
                {
                    "row": idx,
                    "reasons": [f"与第 {seen[dup_key]} 行重复（同一天、同一课程、同一起始时间）"],
                    "raw": row,
                }
            )
            continue
        seen[dup_key] = idx

        ok.append(
            {
                "row_no": idx,
                "course_name": name[:120],
                "weekday": weekday,
                "start_time": start,
                "end_time": end,
                "location": (location or "")[:120] or None,
                "teacher": (teacher or "")[:60] or None,
                "weeks": (weeks or "")[:60] or None,
                "note": (note or "")[:500] or None,
            }
        )

    return ok, bad


def schedule_template_csv() -> bytes:
    """生成课表导入模板（CSV，带 BOM 便于 Excel 直接打开不乱码）"""
    lines = [
        "课程名称,星期,开始时间,结束时间,上课地点,任课教师,周次,备注",
        "高等数学,周一,08:00,09:40,教一101,张伟,1-16,带上教材",
        "数据结构,周三,14:00,15:40,实验楼302,李娜,1-16,",
        "英语口语,周五,16:00,17:30,外语楼102,Smith,1-16,",
    ]
    return ("\ufeff" + "\n".join(lines) + "\n").encode("utf-8")
