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
    OutlineGenerateRequest,
)

logger = structlog.get_logger()

# 内置示例大纲（LLM 不可用或演示时使用）
_SAMPLE_PATH = Path(__file__).resolve().parent.parent / "data" / "sample_outline_math_7a.json"

# 已知课程标准官方出处（联网检索不可用时，LLM 依据这些权威材料梳理）
_KNOWN_CURRICULUM_STANDARDS = {
    "math": {"title": "义务教育数学课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "physics": {"title": "义务教育物理课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "chemistry": {"title": "义务教育化学课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "chinese": {"title": "义务教育语文课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
    "english": {"title": "义务教育英语课程标准（2022年版）", "publisher": "中华人民共和国教育部", "url": "http://www.moe.gov.cn/srcsite/A26/s8001/202204/t20220420_619921.html"},
}

SYSTEM_PROMPT = """你是一名资深课程与教学专家，精通中国各学段国家课程标准与主流教材。
你的任务：依据课程标准及配套材料，为用户指定的课程梳理出「主要学习内容与要求清单、内容间必要联系、材料出处」。

硬性要求：
1. 范围清楚：明确界定梳理边界（学段/年级/教材版本/章节），不超纲、不遗漏主干内容。
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
        except Exception as exc:  # noqa: BLE001 — 统一落库失败原因
            logger.warning("curriculum_generate_failed", error=str(exc), course=data.course_query)
            record.status = "failed"
            record.error_message = str(exc)[:1000]
            await self.db.commit()
            await self.db.refresh(record)
            # LLM 不可用时按需回退示例
            if data.fallback_sample:
                return await self._save_sample_outline(record, data, fallback_reason=str(exc))
            raise AppException(
                code=503,
                message=(
                    "课程梳理依赖大模型服务，当前所有模型均未配置 API Key。"
                    "请在 backend/.env 中配置 DEEPSEEK_API_KEY / QWEN_API_KEY / HUNYUAN_API_KEY 之一后重试；"
                    "或在请求中传 fallback_sample=true 先查看内置示例大纲。"
                ),
            )

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
                out.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", "") or r.get("url", ""),
                        "snippet": r.get("body", "") or r.get("description", ""),
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
                {
                    "title": std["title"],
                    "url": std["url"],
                    "source_type": "curriculum_standard",
                    "publisher": std["publisher"],
                    "usage": "作为各内容要求表述的依据",
                },
            )
            seen_urls.add(std["url"])
        if used_web:
            for r in search_results[:5]:
                if r.get("url") and r["url"] not in seen_urls:
                    outline.sources.append(
                        {
                            "title": r.get("title", "网络材料"),
                            "url": r["url"],
                            "source_type": "web",
                            "publisher": "",
                            "usage": "联网检索参考材料",
                        }
                    )
                    seen_urls.add(r["url"])
        outline.used_web_search = used_web or bool(outline.sources)

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
            lines.append(f"- **生成模型**：{data.model}" + ("（内置示例）" if data.is_sample else ""))
        lines.append(f"- **联网检索**：{'是' if data.used_web_search else '否'}")
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
                hours = str(c.suggested_hours) if c.suggested_hours is not None else "-"
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
            meta.add_run(f"　生成模型：{data.model}" + ("（内置示例）" if data.is_sample else ""))

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
                row[5].text = str(c.suggested_hours) if c.suggested_hours is not None else "-"
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
