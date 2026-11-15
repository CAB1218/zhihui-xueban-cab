"""
智慧学伴 OCR/ASR 提取 Celery 任务
异步处理板书图片 OCR 和录播视频 ASR

任务流程:
1. 从 DB 读取 ClassroomRecord（status=pending）
2. 标记 status=processing
3. 调用 ocr_provider.extract() / asr_provider.transcribe()
4. 更新 transcript + knowledge_points + status=completed
5. 更新 ES 索引（doc_type=classroom_record）
6. 异常 → status=failed + error_msg
"""
import asyncio
import json
import logging
from datetime import datetime

from app.core.celery_app import celery_app, get_sync_session

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.extraction_tasks.process_board_ocr")
def process_board_ocr(record_id: int) -> dict:
    """板书图片 OCR 提取任务

    Args:
        record_id: classroom_records 表记录 ID

    Returns:
        {"status": "completed"/"failed", "record_id": record_id, "error": ...}
    """
    logger.info("[OCR] 开始处理板书记录: record_id=%s", record_id)

    session = get_sync_session()
    try:
        from app.models.teacher_method import ClassroomRecord

        # 读取记录
        record = session.query(ClassroomRecord).filter(
            ClassroomRecord.id == record_id
        ).first()

        if not record:
            logger.error("[OCR] 记录不存在: record_id=%s", record_id)
            return {"status": "failed", "record_id": record_id, "error": "记录不存在"}

        # 标记为 processing
        record.status = "processing"
        record.updated_at = datetime.utcnow()
        session.commit()

        # 调用 OCR Provider（异步函数，需在事件循环中执行）
        from app.services.ocr_service import ocr_provider

        result = asyncio.run(ocr_provider.extract(record.file_url or ""))

        # 更新记录
        record.transcript = result.text
        record.provider = result.provider
        record.status = "completed"
        record.updated_at = datetime.utcnow()
        record.error_msg = None

        # 尝试提取知识点（通过 LLM）
        knowledge_points = _extract_knowledge_points_sync(result.text)
        record.knowledge_points = json.dumps(knowledge_points, ensure_ascii=False) if knowledge_points else None

        session.commit()
        logger.info("[OCR] 处理完成: record_id=%s, provider=%s", record_id, result.provider)

        # 更新 ES 索引（不阻塞主流程）
        try:
            _index_to_es_sync(record)
        except Exception as es_err:
            logger.warning("[OCR] ES 索引更新失败（不影响主流程）: %s", es_err)

        return {
            "status": "completed",
            "record_id": record_id,
            "provider": result.provider,
            "text_length": len(result.text),
        }

    except Exception as e:
        logger.error("[OCR] 处理失败: record_id=%s, error=%s", record_id, e)
        # 标记为 failed
        try:
            record = session.query(ClassroomRecord).filter(
                ClassroomRecord.id == record_id
            ).first()
            if record:
                record.status = "failed"
                record.error_msg = str(e)[:1000]
                record.updated_at = datetime.utcnow()
                session.commit()
        except Exception:
            pass

        return {"status": "failed", "record_id": record_id, "error": str(e)}

    finally:
        session.close()


@celery_app.task(name="app.tasks.extraction_tasks.process_video_asr")
def process_video_asr(record_id: int) -> dict:
    """录播视频 ASR 语音转文字任务

    Args:
        record_id: classroom_records 表记录 ID

    Returns:
        {"status": "completed"/"failed", "record_id": record_id, "error": ...}
    """
    logger.info("[ASR] 开始处理录播记录: record_id=%s", record_id)

    session = get_sync_session()
    try:
        from app.models.teacher_method import ClassroomRecord

        # 读取记录
        record = session.query(ClassroomRecord).filter(
            ClassroomRecord.id == record_id
        ).first()

        if not record:
            logger.error("[ASR] 记录不存在: record_id=%s", record_id)
            return {"status": "failed", "record_id": record_id, "error": "记录不存在"}

        # 标记为 processing
        record.status = "processing"
        record.updated_at = datetime.utcnow()
        session.commit()

        # 调用 ASR Provider（异步函数）
        from app.services.asr_service import asr_provider

        result = asyncio.run(asr_provider.transcribe(record.file_url or ""))

        # 更新记录
        record.transcript = result.transcript
        record.segments = json.dumps(result.segments, ensure_ascii=False) if result.segments else None
        record.provider = result.provider
        record.status = "completed"
        record.updated_at = datetime.utcnow()
        record.error_msg = None

        # 提取知识点
        knowledge_points = _extract_knowledge_points_sync(result.transcript)
        record.knowledge_points = json.dumps(knowledge_points, ensure_ascii=False) if knowledge_points else None

        session.commit()
        logger.info("[ASR] 处理完成: record_id=%s, provider=%s", record_id, result.provider)

        # 更新 ES 索引
        try:
            _index_to_es_sync(record)
        except Exception as es_err:
            logger.warning("[ASR] ES 索引更新失败（不影响主流程）: %s", es_err)

        return {
            "status": "completed",
            "record_id": record_id,
            "provider": result.provider,
            "transcript_length": len(result.transcript),
            "segment_count": len(result.segments),
        }

    except Exception as e:
        logger.error("[ASR] 处理失败: record_id=%s, error=%s", record_id, e)
        try:
            record = session.query(ClassroomRecord).filter(
                ClassroomRecord.id == record_id
            ).first()
            if record:
                record.status = "failed"
                record.error_msg = str(e)[:1000]
                record.updated_at = datetime.utcnow()
                session.commit()
        except Exception:
            pass

        return {"status": "failed", "record_id": record_id, "error": str(e)}

    finally:
        session.close()


def _extract_knowledge_points_sync(text: str) -> list:
    """从文本中提取知识点（MVP：简单关键词匹配，LLM 不可用时返回空列表）

    Args:
        text: OCR/ASR 提取的文本

    Returns:
        知识点列表，如 ["导数", "极限"]
    """
    if not text:
        return []

    # MVP 阶段：简单关键词匹配
    keyword_pool = [
        "函数", "极限", "连续性", "导数", "积分", "微分",
        "向量", "矩阵", "概率", "统计", "方程", "不等式",
        "力学", "电学", "光学", "热学", "牛顿定律", "能量守恒",
        "化学反应", "氧化还原", "酸碱", "有机化学",
    ]

    found = [kw for kw in keyword_pool if kw in text]
    return found[:10]  # 最多返回 10 个


def _index_to_es_sync(record) -> None:
    """将课堂记录索引到 Elasticsearch（同步调用）

    使用 httpx 同步客户端，复用 search_service 的 ES 索引模式。
    索引名: ai4edu，doc_type: classroom_record
    """
    import httpx
    from app.config import settings

    es_host = settings.ELASTICSEARCH_HOST
    index_name = "ai4edu"
    doc_id = f"classroom_record_{record.id}"

    doc_body = {
        "doc_type": "classroom_record",
        "tenant_id": record.tenant_id,
        "record_type": record.record_type,
        "transcript": record.transcript or "",
        "knowledge_points": json.loads(record.knowledge_points) if record.knowledge_points else [],
        "classroom_id": record.classroom_id,
        "course_id": record.course_id,
        "provider": record.provider,
        "created_at": record.created_at.isoformat() if record.created_at else None,
        "updated_at": record.updated_at.isoformat() if record.updated_at else None,
    }

    url = f"{es_host}/{index_name}/_doc/{doc_id}"
    with httpx.Client(timeout=10) as client:
        response = client.put(url, json=doc_body)
        response.raise_for_status()

    logger.info("[ES] 课堂记录已索引: record_id=%s, doc_id=%s", record.id, doc_id)
