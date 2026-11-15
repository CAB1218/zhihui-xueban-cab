"""
智慧学伴 遥测数据接收 API
接收前端上报的性能、错误、用户行为等遥测数据
"""
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/telemetry")
async def receive_telemetry(request: Request) -> dict:
    """
    接收前端遥测数据
    支持批量上报，数据写入 ClickHouse analytics_events 表
    """
    try:
        body = await request.json()
        events = body.get("events", [])
        session_id = body.get("sessionId", "unknown")
        user_agent = body.get("userAgent", "")
        page_url = body.get("url", "")

        if not events:
            return {"status": "ok", "processed": 0}

        # 写入 ClickHouse（异步非阻塞）
        processed = 0
        for event in events:
            event_type = event.get("type", "unknown")
            payload = event.get("payload", {})

            # 构建分析事件
            analytics_event = {
                "event_type": f"frontend_{event_type}",
                "user_id": _get_user_id(request),
                "session_id": session_id,
                "resource_id": page_url,
                "metadata": {
                    "user_agent": user_agent,
                    "page_url": page_url,
                    **_flatten_payload(payload),
                },
            }

            # 尝试写入 ClickHouse
            try:
                await _write_to_clickhouse(analytics_event)
                processed += 1
            except Exception as e:
                logger.warning(f"Failed to write telemetry to ClickHouse: {e}")
                # 静默失败，不影响前端

        return {"status": "ok", "processed": processed}

    except Exception as e:
        logger.error(f"Telemetry endpoint error: {e}")
        return {"status": "error", "message": "Failed to process telemetry"}


def _get_user_id(request: Request) -> str:
    """从请求中提取用户ID"""
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    return "anonymous"


def _flatten_payload(payload: Any, prefix: str = "") -> dict:
    """展平嵌套的 payload 数据"""
    if not isinstance(payload, dict):
        return {f"{prefix}value": str(payload)} if prefix else {"value": str(payload)}

    result = {}
    for key, value in payload.items():
        full_key = f"{prefix}{key}" if not prefix else f"{prefix}_{key}"
        if isinstance(value, dict):
            result.update(_flatten_payload(value, full_key))
        elif isinstance(value, (list, tuple)):
            result[full_key] = str(value)
        else:
            result[full_key] = value
    return result


async def _write_to_clickhouse(event: dict) -> None:
    """写入 ClickHouse analytics_events 表"""
    import httpx

    ch_url = f"http://{settings.CLICKHOUSE_HOST}:{settings.CLICKHOUSE_HTTP_PORT}"
    event_type = event.get("event_type", "unknown")
    user_id = event.get("user_id", "anonymous")
    session_id = event.get("session_id", "")
    resource_id = event.get("resource_id", "")
    metadata = event.get("metadata", {})

    # 将 metadata 转为 JSON 字符串
    import json
    metadata_json = json.dumps(metadata, ensure_ascii=False).replace("'", "''")

    sql = f"""INSERT INTO ai4edu.analytics_events
        (event_type, user_id, session_id, resource_id, metadata, timestamp)
        VALUES ('{event_type}', '{user_id}', '{session_id}', '{resource_id}', '{metadata_json}', now())"""

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.post(
            f"{ch_url}/?user={settings.CLICKHOUSE_USER}&password={settings.CLICKHOUSE_PASSWORD}&database=ai4edu",
            content=sql,
        )
        response.raise_for_status()
