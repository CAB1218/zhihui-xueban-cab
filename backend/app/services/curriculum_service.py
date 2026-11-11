"""
AI4EDU 课程梳理服务
对应任务1（理解学科-学习内容与要求梳理）：
  用户输入想学的课程 → 联网检索课程材料 → LLM 依据课程标准梳理
  → 产出「学习内容与要求清单 + 必要联系 + 材料出处」
  → 支持 JSON / Markdown / Word 三种格式导出，供后续学情分析与学习建议使用
"""
import asyncio
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.llm_router import llm_router
from app.core.exceptions import AppException
from app.models.curriculum import CurriculumOutline
from app.schemas.curriculum import (
    CurriculumOutlineData,
    MaterialSource,
    OutlineGenerateRequest,
)

logger = structlog.get_logger()

# 内置示例大纲（LLM 不可用或演示时使用）
_SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_outline_math_7a.json"
# 内置知识包（离线梳理引擎的依据：无 API Key 时也能产出贴合输入的完整梳理成果）
_PACKS_PATH = Path(__file__).resolve().parent.parent / "data" / "curriculum_packs.json"

# 学科识别关键词
_SUBJECT_HINTS: Dict[str, List[str]] = {
    "math": ["数学", "高数", "微积分", "代数", "几何", "概率", "统计", "线性代数", "函数"],
    "physics": ["物理", "力学", "电磁", "光学", "热学", "大学物理"],
    "chemistry": ["化学", "无机", "有机", "反应"],
    "biology": ["生物", "遗传", "细胞"],
    "cs": ["数据结构", "算法", "编程", "计算机", "操作系统", "网络", "数据库", "程序", "软件", "人工智能"],
    "chinese": ["语文", "现代文", "文言文", "作文", "阅读"],
    "english": ["英语", "英文", "四级", "六级", "雅思", "托福"],
    "history": ["历史", "近代史", "古代史"],
    "geography": ["地理", "气候", "地形"],
    "politics": ["政治", "思想", "道德", "法治"],
}

# 已知课程标准官方出处（联网检索不可用时，LLM 依据这些权威材料梳理）
_KNOWN_CURRICULUM_STANDARDS = {
    "math": {"title": "义务教育数学课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "physics": {"title": "义务教育物理课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "chemistry": {"title": "义务教育化学课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "chinese": {"title": "义务教育语文课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "english": {"title": "义务教育英语课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "cs": {"title": "《计算机类专业教学质量国家标准》", "publisher": "教育部高等学校计算机类专业教学指导委员会", "url": "http://www.moe.gov.cn"},
    "biology": {"title": "义务教育生物学课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "history": {"title": "义务教育历史课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "geography": {"title": "义务教育地理课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "politics": {"title": "义务教育道德与法治课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
}

# 学段识别（用于知识包匹配时排除跨学段误配，例如「初中物理」不应命中《大学物理》）
_LEVEL_HINTS: Dict[str, List[str]] = {
    "primary": ["小学", "一年级", "二年级", "三年级", "四年级", "五年级", "六年级"],
    "junior": ["初中", "七年级", "初一", "八年级", "初二", "九年级", "初三"],
    "senior": ["高中", "高一", "高二", "高三"],
    "college": ["大学", "大一", "大二", "大三", "大四", "本科", "研究生", "专科"],
}

# 联网检索结果里需要过滤掉的无信息量站点（搜索引擎页、翻译、导航等）
_WEB_BLACKLIST_DOMAINS = (
    "google.", "yahoo.", "bing.", "baidu.com/s", "translate.", "duckduckgo.",
    "yandex.", "naver.", "sogou.", "so.com", "haosou.", "w3.org",
)

SYSTEM_PROMPT = """你是一名资深课程与教学专家，精通中国各学段国家课程标准与主流教材。
你的任务：依据课程标准及配套材料，为用户指定的课程梳理出「主要学习内容与要求清单、内容间必要联系、材料出处」。

硬性要求：
1. 范围清楚：明确界定梳理边界（学段/年级/教材版本/章节/主题），用 scope 写清一段话，并在 scope_included（覆盖什么）与 scope_excluded（不覆盖什么）中逐条列出；不超纲、不遗漏主干内容。
2. 要求表述准确：每条内容给出课标风格的「要求」句（使用 了解/理解/掌握/运用/经历/体验/感悟 等行为动词），并标注认知水平（remember/understand/apply/analyze/evaluate/create）。
3. 必要联系：给出前置(prerequisite)/相关(related)/跨学科(cross_subject)联系，说明为什么先学它、如何迁移。
4. 材料出处：每份引用材料给出名称、发布方、链接与在本大纲中的用途；课程标准类出处优先使用教育部官方发布。
5. 只输出 JSON，不要输出任何解释文字或 markdown 代码块围栏。

输出 JSON 结构（严格遵守）：
{
  "course": "课程名",
  "subject": "math|physics|chemistry|biology|cs|chinese|english|history|geography|politics",
  "subject_name": "学科中文名",
  "grade_level": "学段年级",
  "scope": "本次梳理的范围说明（一段话）",
  "scope_included": ["本次明确覆盖的范围，逐条列出单元/章节/主题"],
  "scope_excluded": ["本次不覆盖或仅作了解的内容，逐条列出，用于界定边界"],
  "units": [
    {
      "name": "单元名",
      "description": "单元简介与定位",
      "textbook_ref": "教材章节出处",
      "contents": [
        {
          "topic": "内容主题",
          "description": "内容说明",
          "requirement": "课标要求表述句",
          "requirement_level": "了解|理解|掌握|运用|经历|体验|感悟",
          "cognitive_level": "remember|understand|apply|analyze|evaluate|create",
          "suggested_hours": 2
        }
      ]
    }
  ],
  "connections": [
    {"from_topic": "主题A", "to_topic": "主题B", "link_type": "prerequisite|related|cross_subject", "description": "联系说明"}
  ],
  "sources": [
    {"title": "材料名", "publisher": "发布方", "url": "链接", "source_type": "curriculum_standard|textbook|exam_outline|web", "usage": "用途"}
  ]
}"""


class CurriculumService:
    """课程梳理：检索 → LLM 梳理 → 结构化大纲 → 多格式导出"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # 对外主流程
    # ------------------------------------------------------------------

    async def generate_outline(
        self,
        user_id: int,
        tenant_id: int,
        data: OutlineGenerateRequest,
    ) -> CurriculumOutline:
        """生成课程梳理大纲并落库"""
        record = CurriculumOutline(
            tenant_id=tenant_id,
            user_id=user_id,
            course_query=data.course_query,
            subject=data.subject,
            grade_level=data.grade_level,
            scope_hint=data.scope_hint,
            status="pending",
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)

        try:
            outline_data, search_results, used_web, model_name = await self._build_outline(data)
            record.title = outline_data.course
            record.subject = outline_data.subject
            record.grade_level = outline_data.grade_level or data.grade_level
            record.outline = outline_data.model_dump_json()
            record.sources_json = json.dumps(search_results, ensure_ascii=False)
            record.model_name = model_name
            record.used_web_search = used_web
            record.status = "completed"
        except Exception as exc:  # noqa: BLE001 — 大模型不可用时统一走离线梳理
            logger.warning("curriculum_llm_failed", error=str(exc)[:300], course=data.course_query)
            record.error_message = f"大模型调用失败：{str(exc)[:300]}"

            # 第一优先级：内置知识包离线梳理（无 API Key 也能给出贴合输入的完整成果）
            try:
                offline = self.build_offline_outline(data)
            except Exception as offline_exc:  # noqa: BLE001 — 离线引擎异常不应直接 500
                logger.warning("curriculum_offline_failed", error=str(offline_exc)[:300])
                offline = None

            if offline is not None:
                outline_data, pack_note = offline
                record.title = outline_data.course
                record.subject = outline_data.subject
                record.grade_level = outline_data.grade_level or data.grade_level
                record.outline = outline_data.model_dump_json()
                record.sources_json = json.dumps(
                    [s.model_dump() for s in outline_data.sources], ensure_ascii=False
                )
                record.model_name = outline_data.model
                record.used_web_search = False
                record.status = "completed"
                record.error_message = (f"{record.error_message or ''}；已使用{pack_note}")[:1000]
            elif data.fallback_sample:
                return await self._save_sample_outline(record, data, fallback_reason=str(exc))
            else:
                record.status = "failed"
                await self.db.commit()
                await self.db.refresh(record)
                raise AppException(
                    code=503,
                    message=(
                        "课程梳理需要大模型或内置知识包支持：当前未配置任何大模型 API Key，"
                        "且未匹配到内置知识包。请在 backend/.env 配置 DEEPSEEK_API_KEY / QWEN_API_KEY / "
                        "HUNYUAN_API_KEY 之一后重试；也可勾选「LLM 不可用时可回退内置示例」，"
                        "或在课程名中使用内置包覆盖的课程（数据结构 / 高等数学 / 线性代数 / 大学物理 / 初中数学）。"
                    ),
                )

        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # 文件导入（课表 / 大纲 / 导出过的 JSON）
    # ------------------------------------------------------------------

    _SUBJECT_NAMES: Dict[str, str] = {
        "math": "数学",
        "physics": "物理",
        "chemistry": "化学",
        "biology": "生物",
        "cs": "计算机科学",
        "chinese": "语文",
        "english": "英语",
        "history": "历史",
        "geography": "地理",
        "politics": "政治",
    }

    async def save_imported_outline(
        self,
        user_id: int,
        tenant_id: int,
        *,
        filename: str,
        skeleton: Dict[str, Any],
    ) -> CurriculumOutline:
        """把导入文件解析出的骨架存为一条已完成的梳理记录。

        skeleton 来自 import_service 的三种解析器：
        - 带 "outline" 键：完整的 outline JSON（本系统导出格式），直接校验入库
        - 否则为 {course, subject_hint, grade_level, textbook_ref, units, skipped_rows}
        """
        now = datetime.now(timezone.utc).isoformat()

        if "outline" in skeleton:
            raw = skeleton["outline"]
            raw["generated_at"] = raw.get("generated_at") or now
            raw["model"] = "文件导入"
            raw["used_web_search"] = False
            raw["is_sample"] = False
            outline_data = CurriculumOutlineData.model_validate(raw)
        else:
            course = skeleton["course"]
            subject = self._detect_subject(
                " ".join(filter(None, [course, skeleton.get("subject_hint", "")])),
                None,
            ) or "math"
            units = skeleton["units"]
            content_count = sum(len(u.get("contents", [])) for u in units)
            skipped = skeleton.get("skipped_rows", 0)

            scope = (
                f"本大纲由上传文件《{filename}》导入生成，共 {len(units)} 个单元、"
                f"{content_count} 条学习内容。单元与内容来自用户提供的课表/大纲文件；"
                "「要求表述」与「必要联系」如需按课程标准细化，可再使用「生成课程梳理」流程补全。"
            )
            if skipped:
                scope += f"另有 {skipped} 行因缺少学习内容列而未纳入。"

            sources: List[Dict[str, Any]] = [
                {
                    "title": f"上传文件：{filename}",
                    "url": "",
                    "source_type": "upload",
                    "publisher": "用户上传",
                    "usage": "本大纲的单元与学习内容清单直接来自该文件",
                }
            ]
            if skeleton.get("textbook_ref"):
                sources.append(
                    {
                        "title": f"《{course}》教材（{skeleton['textbook_ref']}）",
                        "url": "",
                        "source_type": "textbook",
                        "publisher": "",
                        "usage": "文件标注的教材出处",
                    }
                )

            outline_data = CurriculumOutlineData.model_validate(
                {
                    "course": course,
                    "subject": subject,
                    "subject_name": self._SUBJECT_NAMES.get(subject, skeleton.get("subject_hint") or "通用"),
                    "grade_level": skeleton.get("grade_level") or "",
                    "scope": scope,
                    "scope_included": [
                        f"第{i}单元 {u.get('name', '')}（{len(u.get('contents', []))} 条）"
                        for i, u in enumerate(units, 1)
                    ],
                    "scope_excluded": [],
                    "units": units,
                    "connections": [],
                    "sources": sources,
                    "generated_at": now,
                    "model": "文件导入",
                    "used_web_search": False,
                    "is_sample": False,
                }
            )

        # 保证材料出处中始终标注上传文件本身
        if not any(s.source_type == "upload" for s in outline_data.sources):
            outline_data.sources.insert(
                0,
                MaterialSource(
                    title=f"上传文件：{filename}",
                    url="",
                    source_type="upload",
                    publisher="用户上传",
                    usage="本大纲的单元与学习内容清单直接来自该文件",
                ),
            )

        record = CurriculumOutline(
            tenant_id=tenant_id,
            user_id=user_id,
            course_query=outline_data.course,
            subject=outline_data.subject,
            grade_level=outline_data.grade_level,
            scope_hint=f"文件导入：{filename}",
            title=outline_data.course,
            outline=outline_data.model_dump_json(),
            sources_json=json.dumps(
                [s.model_dump() for s in outline_data.sources], ensure_ascii=False
            ),
            model_name="文件导入",
            used_web_search=False,
            status="completed",
        )
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def get_outline(self, outline_id: int, user_id: int, is_admin: bool = False) -> CurriculumOutline:
        record = await self.db.get(CurriculumOutline, outline_id)
        if not record:
            raise AppException(code=404, message="课程梳理记录不存在")
        if not is_admin and record.user_id != user_id:
            raise AppException(code=403, message="无权访问该课程梳理记录")
        return record

    async def list_outlines(
        self,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[CurriculumOutline], int]:
        from sqlalchemy import func, select

        stmt = select(CurriculumOutline).where(CurriculumOutline.user_id == user_id)
        count_stmt = select(func.count()).select_from(CurriculumOutline).where(CurriculumOutline.user_id == user_id)
        total = (await self.db.execute(count_stmt)).scalar() or 0
        rows = (
            await self.db.execute(
                stmt.order_by(CurriculumOutline.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        ).scalars().all()
        return list(rows), int(total)

    # ------------------------------------------------------------------
    # 导出（JSON / Markdown / Word）
    # ------------------------------------------------------------------

    async def export_outline(
        self, outline_id: int, user_id: int, fmt: str, is_admin: bool = False
    ) -> Tuple[bytes, str, str]:
        """导出为 (bytes, filename, media_type)"""
        record = await self.get_outline(outline_id, user_id, is_admin)
        if not record.outline:
            raise AppException(code=404, message="该记录没有可导出的大纲内容")

        data = CurriculumOutlineData.model_validate_json(record.outline)
        safe_name = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", data.course or record.course_query)[:40]

        if fmt == "json":
            payload = json.dumps(data.model_dump(), ensure_ascii=False, indent=2)
            return payload.encode("utf-8"), f"课程梳理_{safe_name}.json", "application/json"

        if fmt == "md":
            md = self.render_markdown(data)
            return md.encode("utf-8"), f"课程梳理_{safe_name}.md", "text/markdown"

        if fmt == "docx":
            docx_bytes = self.render_docx(data)
            return docx_bytes, f"课程梳理_{safe_name}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        raise AppException(code=400, message=f"不支持的导出格式: {fmt}")

    # ------------------------------------------------------------------
    # 内部：检索 + LLM
    # ------------------------------------------------------------------

    async def _build_outline(
        self, data: OutlineGenerateRequest
    ) -> Tuple[CurriculumOutlineData, List[Dict[str, Any]], bool, str]:
        """返回 (大纲, 检索结果, 是否用了联网, 模型名)"""
        search_results: List[Dict[str, Any]] = []
        used_web = False
        if data.use_web_search:
            search_results = await self._web_search(self._build_search_query(data))
            used_web = bool(search_results)
            logger.info("curriculum_web_search", query=data.course_query, hits=len(search_results), success=used_web)

        result = await llm_router.call_llm(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._build_user_prompt(data, search_results)},
            ],
            scene_type="curriculum_outline",
            temperature=0.3,
            max_tokens=6000,
            tenant_id=None,
            user_id=None,
        )
        content = result.get("content") or ""
        model_name = result.get("model") or ""
        outline_data = self._parse_outline_json(content, data)
        self._ensure_sources(outline_data, search_results, used_web)
        return outline_data, search_results, used_web, model_name

    def _build_search_query(self, data: OutlineGenerateRequest) -> str:
        parts = [data.course_query, "课程标准", "教学要求"]
        if data.grade_level:
            parts.insert(1, data.grade_level)
        return " ".join(p for p in parts if p)

    async def _web_search(self, query: str, max_results: int = 8) -> List[Dict[str, Any]]:
        """联网检索课程材料。依赖 duckduckgo-search（ddgs）包，不可用时静默降级为空。"""
        try:
            # 兼容旧包名 duckduckgo_search 与新包名 ddgs
            try:
                from duckduckgo_search import DDGS  # type: ignore
            except ImportError:  # pragma: no cover
                from ddgs import DDGS  # type: ignore
        except ImportError:
            logger.info("curriculum_search_lib_missing")
            return []

        loop = asyncio.get_running_loop()

        def _search() -> List[Dict[str, Any]]:
            with DDGS() as ddgs:  # type: ignore[union-attr]
                raw = list(ddgs.text(query, max_results=max_results, region="cn-zh"))
            out: List[Dict[str, Any]] = []
            for r in raw:
                url = r.get("href", "") or r.get("url", "")
                title = (r.get("title", "") or "").strip()
                snippet = (r.get("body", "") or r.get("description", "") or "").strip()
                if not url or not title:
                    continue
                # 过滤搜索引擎/翻译/导航类无信息量页面，避免污染「材料出处」
                if any(bad in (url or "").lower() for bad in _WEB_BLACKLIST_DOMAINS):
                    continue
                # 至少一个关键词命中标题或摘要，才算与本次梳理相关
                kws = [w for w in re.split(r"[\s，,。;|/]+", query) if len(w) >= 2]
                if kws and not any(w in title or w in snippet for w in kws):
                    continue
                out.append(
                    {
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                        "source_type": "web",
                    }
                )
            return out

        try:
            return await asyncio.wait_for(loop.run_in_executor(None, _search), timeout=25)
        except Exception as exc:  # noqa: BLE001 — 网络问题不阻断主流程
            logger.warning("curriculum_web_search_failed", error=str(exc))
            return []

    def _build_user_prompt(
        self, data: OutlineGenerateRequest, search_results: List[Dict[str, Any]]
    ) -> str:
        lines = [f"请梳理课程：{data.course_query}"]
        if data.subject:
            lines.append(f"指定学科ID：{data.subject}")
        if data.grade_level:
            lines.append(f"学段年级：{data.grade_level}")
        if data.scope_hint:
            lines.append(f"范围限定：{data.scope_hint}")

        std = _KNOWN_CURRICULUM_STANDARDS.get(data.subject or "")
        if std:
            lines.append(f"课程标准权威出处（务必列入 sources）：{std['title']}，{std['publisher']}，{std['url']}")

        if search_results:
            lines.append("以下是联网检索到的课程材料摘要（可作为材料出处与梳理依据）：")
            for i, r in enumerate(search_results, 1):
                lines.append(f"[{i}] {r['title']} | {r['url']} | {r['snippet'][:150]}")
        else:
            lines.append("（本次未能联网检索，请依据你对国家课程标准与主流教材的知识完成梳理，材料出处必须给出真实可查的官方/权威来源。）")
        lines.append("请严格按系统提示中的 JSON 结构输出。")
        return "\n".join(lines)

    def _parse_outline_json(self, content: str, data: OutlineGenerateRequest) -> CurriculumOutlineData:
        text = content.strip()
        # 去掉可能的 markdown 围栏
        fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if fence:
            text = fence.group(1)
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise AppException(code=502, message="LLM 返回内容不是合法 JSON，请重试")
        raw = json.loads(text[start : end + 1])

        now = datetime.now(timezone.utc).isoformat()
        raw.setdefault("course", data.course_query)
        raw.setdefault("grade_level", data.grade_level or "")
        raw.setdefault("scope", data.scope_hint or "")
        raw["generated_at"] = now
        raw["used_web_search"] = False  # 由 _ensure_sources 修正
        raw["is_sample"] = False
        return CurriculumOutlineData.model_validate(raw)

    def _ensure_sources(
        self,
        outline: CurriculumOutlineData,
        search_results: List[Dict[str, Any]],
        used_web: bool,
    ) -> None:
        """补齐材料出处：课标权威出处 + 检索结果，确保可溯源"""
        seen_urls = {s.url for s in outline.sources if s.url}
        std = _KNOWN_CURRICULUM_STANDARDS.get(outline.subject)
        if std and std["url"] not in seen_urls:
            outline.sources.insert(
                0,
                MaterialSource(
                    title=std["title"],
                    url=std["url"],
                    source_type="curriculum_standard",
                    publisher=std["publisher"],
                    usage="作为各内容要求表述的依据",
                ),
            )
            seen_urls.add(std["url"])
        if used_web:
            for r in search_results[:5]:
                if r.get("url") and r["url"] not in seen_urls:
                    outline.sources.append(
                        MaterialSource(
                            title=r.get("title", "网络材料"),
                            url=r["url"],
                            source_type="web",
                            publisher="",
                            usage="联网检索参考材料",
                        )
                    )
                    seen_urls.add(r["url"])
        # 兜底：材料出处至少要有 2 条（课程标准 + 教材/权威参考），保证可溯源
        if len(outline.sources) < 2:
            outline.sources.append(
                MaterialSource(
                    title=f"《{outline.course}》配套教材及教师教学用书",
                    url="",
                    source_type="textbook",
                    publisher="对应出版社（以学校实际选用版本为准）",
                    usage="确定单元划分、章节出处与建议课时",
                )
            )
        outline.used_web_search = used_web

    # ------------------------------------------------------------------
    # 内部：离线梳理引擎（内置知识包，无需大模型）
    # ------------------------------------------------------------------

    _packs_cache: Optional[List[Dict[str, Any]]] = None

    def _load_packs(self) -> List[Dict[str, Any]]:
        """加载内置知识包（含示例大纲作为一门课程的包）"""
        if CurriculumService._packs_cache is not None:
            return CurriculumService._packs_cache

        packs: List[Dict[str, Any]] = []
        try:
            if _PACKS_PATH.exists():
                packs = json.loads(_PACKS_PATH.read_text(encoding="utf-8")).get("packs", [])
        except Exception as exc:  # noqa: BLE001 — 知识包损坏不应阻断服务
            logger.warning("curriculum_packs_load_failed", error=str(exc))

        # 把示例大纲也纳入匹配池（初中数学七年级上册）
        try:
            if _SAMPLE_PATH.exists():
                sample = json.loads(_SAMPLE_PATH.read_text(encoding="utf-8"))
                sample["id"] = "math-junior-7a"
                sample["grades"] = ["七年级", "初一", "初中"]
                sample["keywords"] = ["初中数学", "七年级", "初一", "有理数", "整式", "一元一次方程", "几何图形"]
                sample["excluded"] = ["八年级及以上的函数、三角形相似、圆等内容", "高中数学内容"]
                packs.append(sample)
        except Exception as exc:  # noqa: BLE001
            logger.warning("curriculum_sample_load_failed", error=str(exc))

        CurriculumService._packs_cache = packs
        return packs

    @staticmethod
    def _detect_subject(text: str, explicit: Optional[str] = None) -> Optional[str]:
        """从用户输入推断学科（显式指定优先）"""
        if explicit:
            return explicit
        scores: Dict[str, int] = {}
        for subject, words in _SUBJECT_HINTS.items():
            hit = sum(1 for w in words if w in text)
            if hit:
                scores[subject] = hit
        if not scores:
            return None
        return max(scores.items(), key=lambda kv: kv[1])[0]

    def _score_pack(self, pack: Dict[str, Any], text: str, subject: Optional[str]) -> int:
        """知识包匹配打分"""
        score = 0
        course = pack.get("course", "")
        if course and course in text:
            score += 8
        for kw in pack.get("keywords", []):
            if kw and kw in text:
                score += 3 if len(kw) >= 3 else 2
        if subject:
            if pack.get("subject") == subject:
                score += 4
        for grade in pack.get("grades", []):
            if grade and grade in text:
                score += 1
        # 学段不符（如「初中物理」命中《大学物理》）时重罚，避免给出超纲成果
        user_levels = self._levels_of(text)
        pack_levels = self._levels_of(" ".join(pack.get("grades", [])))
        if user_levels and pack_levels and not (user_levels & pack_levels):
            score -= 8
        return score

    @staticmethod
    def _levels_of(text: str) -> set:
        """识别文本所属学段：primary/junior/senior/college"""
        return {lvl for lvl, words in _LEVEL_HINTS.items() if any(w in text for w in words)}

    def build_offline_outline(
        self, data: OutlineGenerateRequest
    ) -> Optional[Tuple[CurriculumOutlineData, str]]:
        """离线梳理：按输入匹配内置知识包 → 生成带明确范围边界的完整大纲。

        返回 (大纲数据, 使用的知识包说明)；无可用知识包时返回 None。
        """
        text = " ".join(
            filter(None, [data.course_query, data.grade_level, data.scope_hint, data.subject])
        )
        packs = self._load_packs()
        if not packs:
            return None

        subject = self._detect_subject(text, data.subject)
        scored = sorted(
            ((self._score_pack(p, text, subject), p) for p in packs),
            key=lambda item: item[0],
            reverse=True,
        )
        best_score, best = scored[0]
        if best_score < 3:
            logger.info("curriculum_offline_no_match", query=data.course_query, best=best.get("id"))
            return None

        payload = json.loads(json.dumps(best, ensure_ascii=False))  # 深拷贝，避免污染缓存
        units = payload.get("units", [])

        # 范围：默认覆盖整门课程；若用户限定了范围，标出命中的单元/内容
        matched_units: List[str] = []
        matched_topics: List[str] = []
        hint = (data.scope_hint or "").strip()
        if hint:
            for unit in units:
                unit_hit = hint in unit.get("name", "")
                for content in unit.get("contents", []):
                    if hint in content.get("topic", "") or hint in content.get("description", ""):
                        matched_topics.append(content.get("topic", ""))
                        unit_hit = True
                if unit_hit:
                    matched_units.append(unit.get("name", ""))

        content_count = sum(len(u.get("contents", [])) for u in units)
        total_hours = sum(
            (c.get("suggested_hours") or 0) for u in units for c in u.get("contents", [])
        )
        grade = (data.grade_level or "").strip() or (payload.get("grade_level") or "")

        scope_parts = [
            f"本次梳理限于《{data.course_query}》（{grade or '学段未限定'}）范围，"
            f"共 {len(units)} 个单元、{content_count} 条学习内容、建议 {int(total_hours)} 课时。"
        ]
        if hint:
            if matched_topics:
                scope_parts.append(
                    f"限定重点为「{hint}」，涉及单元：{'、'.join(matched_units[:3])}"
                    f"（共命中 {len(matched_topics)} 条内容："
                    f"{'、'.join(matched_topics[:6])}{'等' if len(matched_topics) > 6 else ''}）。"
                    "其余单元保留在清单中作为完整课程框架，不因限定而删减。"
                )
            else:
                scope_parts.append(
                    f"用户限定「{hint}」，但在本课程主干内容中未定位到直接对应条目，"
                    "故按整门课程主干梳理，限定词在「必要联系」中体现。"
                )
        scope_parts.append("范围外内容（先修课程、后续课程、拓展专题）只在「必要联系」中提示，不计入本清单的要求。")
        if best.get("generic"):
            scope_parts.append(
                "说明：本成果为学科模块级通用框架（未接入大模型时使用），单元颗粒度到课标模块；"
                f"配置大模型 API Key 后可细化到《{data.course_query}》的具体版本与章节。"
            )

        payload["course"] = data.course_query.strip()
        payload["subject"] = payload.get("subject") or subject or "cs"
        payload["grade_level"] = grade
        payload["scope"] = "".join(scope_parts)
        payload["scope_included"] = [
            f"第{i}单元 {u.get('name', '')}（{len(u.get('contents', []))} 条）"
            for i, u in enumerate(units, 1)
        ]
        payload["scope_excluded"] = payload.get("excluded", []) or []
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        payload["model"] = f"离线知识包·{best.get('course', '')}"
        payload["used_web_search"] = False
        payload["is_sample"] = True

        payload.pop("excluded", None)
        payload.pop("keywords", None)
        payload.pop("id", None)
        payload.pop("grades", None)

        outline = CurriculumOutlineData.model_validate(payload)
        self._ensure_sources(outline, [], False)
        return outline, f"内置知识包《{best.get('course', '')}》离线梳理"

    # ------------------------------------------------------------------
    # 内部：示例回退
    # ------------------------------------------------------------------

    async def _save_sample_outline(
        self,
        record: CurriculumOutline,
        data: OutlineGenerateRequest,
        fallback_reason: str,
    ) -> CurriculumOutline:
        if not _SAMPLE_PATH.exists():
            raise AppException(code=503, message=fallback_reason)
        sample = json.loads(_SAMPLE_PATH.read_text(encoding="utf-8"))
        sample["course"] = sample.get("course") or data.course_query
        outline = CurriculumOutlineData.model_validate(sample)
        outline.is_sample = True
        record.title = outline.course
        record.subject = outline.subject
        record.grade_level = outline.grade_level
        record.outline = outline.model_dump_json()
        record.sources_json = json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else s for s in outline.sources],
            ensure_ascii=False,
        )
        record.model_name = "builtin-sample"
        record.used_web_search = False
        record.status = "completed"
        record.error_message = f"LLM 不可用，已回退内置示例：{fallback_reason}"[:1000]
        await self.db.commit()
        await self.db.refresh(record)
        return record

    # ------------------------------------------------------------------
    # 渲染：Markdown / Word
    # ------------------------------------------------------------------

    @staticmethod
    def _model_suffix(data: CurriculumOutlineData) -> str:
        """标注成果来源，避免把离线内容误当成大模型生成结果"""
        if not data.is_sample:
            return ""
        if data.model.startswith("离线知识包"):
            return "（离线知识包，未调用大模型）"
        return "（内置示例）"

    def render_markdown(self, data: CurriculumOutlineData) -> str:
        lines: List[str] = []
        level_map = {"prerequisite": "前置", "related": "相关", "cross_subject": "跨学科"}
        lines.append(f"# {data.course} — 学习内容与要求梳理")
        lines.append("")
        lines.append(f"- **学科**：{data.subject_name}（{data.subject}）")
        if data.grade_level:
            lines.append(f"- **学段/年级**：{data.grade_level}")
        if data.scope:
            lines.append(f"- **梳理范围**：{data.scope}")
        lines.append(f"- **生成时间**：{data.generated_at}")
        if data.model:
            lines.append(f"- **生成模型**：{data.model}" + self._model_suffix(data))
        lines.append(f"- **联网检索**：{'是' if data.used_web_search else '否'}")
        lines.append("")

        # 成果概览（便于快速判断范围与规模）
        content_count = sum(len(u.contents) for u in data.units)
        total_hours = sum((c.suggested_hours or 0) for u in data.units for c in u.contents)
        lines.append("## 成果概览")
        lines.append("")
        lines.append(
            f"- 单元数：{len(data.units)}　学习内容：{content_count} 条　建议课时：{int(total_hours)} 课时"
        )
        lines.append(f"- 必要联系：{len(data.connections)} 条　材料出处：{len(data.sources)} 条")
        if data.scope_included:
            lines.append("- **覆盖范围**：" + "；".join(data.scope_included))
        if data.scope_excluded:
            lines.append("- **不覆盖/仅作了解**：" + "；".join(data.scope_excluded))
        lines.append("")

        lines.append("## 一、学习内容与要求清单")
        for ui, unit in enumerate(data.units, 1):
            lines.append("")
            lines.append(f"### {ui}. {unit.name}")
            if unit.description:
                lines.append(f"> {unit.description}")
            if unit.textbook_ref:
                lines.append(f"（教材出处：{unit.textbook_ref}）")
            lines.append("")
            lines.append("| # | 学习内容 | 内容说明 | 要求 | 要求水平 | 认知水平 | 建议课时 |")
            lines.append("|---|---------|---------|------|---------|---------|---------|")
            for ci, c in enumerate(unit.contents, 1):
                hours = (
                    str(int(c.suggested_hours))
                    if c.suggested_hours is not None and float(c.suggested_hours).is_integer()
                    else (str(c.suggested_hours) if c.suggested_hours is not None else "-")
                )
                lines.append(
                    f"| {ci} | {c.topic} | {c.description} | {c.requirement} | {c.requirement_level} | {c.cognitive_level} | {hours} |"
                )

        lines.append("")
        lines.append("## 二、必要联系")
        lines.append("")
        lines.append("| 起始内容 | 指向内容 | 联系类型 | 说明 |")
        lines.append("|---------|---------|---------|------|")
        for link in data.connections:
            lines.append(
                f"| {link.from_topic} | {link.to_topic} | {level_map.get(link.link_type, link.link_type)} | {link.description} |"
            )

        lines.append("")
        lines.append("## 三、材料出处")
        lines.append("")
        type_map = {"curriculum_standard": "课程标准", "textbook": "教材", "exam_outline": "考试大纲", "web": "网络材料"}
        for si, s in enumerate(data.sources, 1):
            lines.append(f"{si}. **{s.title}**（{type_map.get(s.source_type, s.source_type)}）{'　' + s.publisher if s.publisher else ''}")
            if s.url:
                lines.append(f"   - 链接：{s.url}")
            if s.usage:
                lines.append(f"   - 用途：{s.usage}")
        lines.append("")
        return "\n".join(lines)

    def render_docx(self, data: CurriculumOutlineData) -> bytes:
        """渲染为 Word 文档（python-docx），失败时抛出明确错误"""
        try:
            from docx import Document
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Pt
        except ImportError as exc:  # pragma: no cover
            raise AppException(code=500, message="服务器未安装 python-docx，无法导出 Word") from exc

        level_map = {"prerequisite": "前置", "related": "相关", "cross_subject": "跨学科"}
        type_map = {"curriculum_standard": "课程标准", "textbook": "教材", "exam_outline": "考试大纲", "web": "网络材料"}

        doc = Document()
        title = doc.add_heading(f"{data.course} — 学习内容与要求梳理", level=0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER

        meta = doc.add_paragraph()
        meta.add_run(f"学科：{data.subject_name}（{data.subject}）　")
        if data.grade_level:
            meta.add_run(f"学段/年级：{data.grade_level}　")
        if data.scope:
            meta.add_run(f"梳理范围：{data.scope}　")
        meta.add_run(f"生成时间：{data.generated_at}")
        if data.model:
            meta.add_run(f"　生成模型：{data.model}" + self._model_suffix(data))

        # 成果概览
        content_count = sum(len(u.contents) for u in data.units)
        total_hours = sum((c.suggested_hours or 0) for u in data.units for c in u.contents)
        doc.add_paragraph(
            f"成果概览：{len(data.units)} 个单元 / {content_count} 条学习内容 / 建议 {int(total_hours)} 课时 / "
            f"{len(data.connections)} 条必要联系 / {len(data.sources)} 条材料出处"
        )
        if data.scope_included:
            doc.add_paragraph("覆盖范围：" + "；".join(data.scope_included))
        if data.scope_excluded:
            doc.add_paragraph("不覆盖或仅作了解：" + "；".join(data.scope_excluded))

        doc.add_heading("一、学习内容与要求清单", level=1)
        for ui, unit in enumerate(data.units, 1):
            doc.add_heading(f"{ui}. {unit.name}", level=2)
            if unit.description:
                doc.add_paragraph(unit.description)
            if unit.textbook_ref:
                p = doc.add_paragraph()
                run = p.add_run(f"教材出处：{unit.textbook_ref}")
                run.italic = True
            table = doc.add_table(rows=1, cols=6)
            table.style = "Table Grid"
            headers = ["学习内容", "内容说明", "要求", "要求水平", "认知水平", "建议课时"]
            for i, h in enumerate(headers):
                cell = table.rows[0].cells[i]
                cell.text = h
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.bold = True
                        run.font.size = Pt(10)
            for c in unit.contents:
                row = table.add_row().cells
                row[0].text = c.topic
                row[1].text = c.description
                row[2].text = c.requirement
                row[3].text = c.requirement_level
                row[4].text = c.cognitive_level
                row[5].text = (
                    str(int(c.suggested_hours))
                    if c.suggested_hours is not None and float(c.suggested_hours).is_integer()
                    else (str(c.suggested_hours) if c.suggested_hours is not None else "-")
                )
            doc.add_paragraph()

        doc.add_heading("二、必要联系", level=1)
        table = doc.add_table(rows=1, cols=4)
        table.style = "Table Grid"
        for i, h in enumerate(["起始内容", "指向内容", "联系类型", "说明"]):
            cell = table.rows[0].cells[i]
            cell.text = h
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    run.font.bold = True
        for link in data.connections:
            row = table.add_row().cells
            row[0].text = link.from_topic
            row[1].text = link.to_topic
            row[2].text = level_map.get(link.link_type, link.link_type)
            row[3].text = link.description
        doc.add_paragraph()

        doc.add_heading("三、材料出处", level=1)
        for si, s in enumerate(data.sources, 1):
            p = doc.add_paragraph(style="List Number")
            p.add_run(f"{s.title}").bold = True
            p.add_run(f"（{type_map.get(s.source_type, s.source_type)}{'，' + s.publisher if s.publisher else ''}）")
            if s.url:
                doc.add_paragraph(f"链接：{s.url}", style="List Bullet")
            if s.usage:
                doc.add_paragraph(f"用途：{s.usage}", style="List Bullet")

        import io

        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()
