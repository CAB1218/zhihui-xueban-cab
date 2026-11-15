"""
智慧学伴 分析事件 Service
ClickHouse 事件追踪
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from app.config import settings
from app.models.analytics import EventType

logger = logging.getLogger(__name__)


class AnalyticsService:
    """分析事件服务"""

    def __init__(self):
        self.ch_host = settings.CLICKHOUSE_HOST
        self.ch_port = settings.CLICKHOUSE_PORT
        self.ch_user = settings.CLICKHOUSE_USER
        self.ch_password = settings.CLICKHOUSE_PASSWORD

    async def track_event(
        self,
        user_id: Optional[int],
        event_type: str,
        event_data: Optional[Dict[str, Any]] = None,
        tenant_id: Optional[int] = None,
    ) -> bool:
        """
        追踪分析事件到 ClickHouse

        Args:
            user_id: 用户ID
            event_type: 事件类型（8种之一）
            event_data: 事件数据
            tenant_id: 租户ID

        Returns:
            是否追踪成功
        """
        # 验证事件类型
        valid_types = {
            EventType.PAGE_VIEW,
            EventType.RESOURCE_UPLOAD,
            EventType.RESOURCE_DOWNLOAD,
            EventType.SEARCH_QUERY,
            EventType.GRAPH_BROWSE,
            EventType.NODE_CLICK,
            EventType.AI_CHAT,
            EventType.SCENE_SWITCH,
        }
        if event_type not in valid_types:
            logger.warning(f"无效的事件类型: {event_type}")
            return False

        event_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        event_data_json = json.dumps(event_data or {}, ensure_ascii=False)

        # 插入到 ClickHouse
        try:
            query = (
                "INSERT INTO analytics_events (id, user_id, tenant_id, event_type, event_data, timestamp) "
                "VALUES (?, ?, ?, ?, ?, ?)"
            )
            await self._execute_clickhouse(query, [
                event_id,
                user_id or 0,
                tenant_id or 0,
                event_type,
                event_data_json,
                timestamp,
            ])
            return True
        except Exception as e:
            logger.error(f"ClickHouse 事件追踪失败: {e}")
            return False

    async def _execute_clickhouse(self, query: str, params: list) -> None:
        """执行 ClickHouse HTTP 接口查询"""
        url = f"http://{self.ch_host}:8123/"
        params_dict = {
            "database": "ai4edu",
            "user": self.ch_user,
            "password": self.ch_password,
        }

        # 构建 INSERT 语句：将 ? 占位符替换为 ClickHouse 兼容的值
        if params:
            escaped = []
            for p in params:
                if isinstance(p, str):
                    # 转义单引号防止注入
                    escaped.append(f"'{p.replace(chr(39), chr(39)+chr(39))}'")
                elif isinstance(p, bool):
                    escaped.append('1' if p else '0')
                elif p is None:
                    escaped.append('NULL')
                else:
                    escaped.append(str(p))
            query_with_values = query
            for val in escaped:
                query_with_values = query_with_values.replace('?', val, 1)
        else:
            query_with_values = query

        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, params=params_dict, content=query_with_values)

    async def get_event_stats(
        self,
        event_type: Optional[str] = None,
        user_id: Optional[int] = None,
        tenant_id: Optional[int] = None,
        days: int = 7,
    ) -> Dict[str, Any]:
        """
        获取事件统计
        """
        conditions = []
        if event_type:
            # 参数化防注入
            safe_type = event_type.replace("'", "''")
            conditions.append(f"event_type = '{safe_type}'")
        if user_id:
            conditions.append(f"user_id = {int(user_id)}")
        if tenant_id:
            conditions.append(f"tenant_id = {int(tenant_id)}")
        conditions.append(f"timestamp >= now() - INTERVAL {int(days)} DAY")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"SELECT event_type, count() AS cnt FROM analytics_events WHERE {where_clause} GROUP BY event_type ORDER BY cnt DESC"

        try:
            url = f"http://{self.ch_host}:8123/"
            params_dict = {
                "database": "ai4edu",
                "user": self.ch_user,
                "password": self.ch_password,
            }

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, params=params_dict, content=query)
                return {"stats": response.text.strip()}
        except Exception as e:
            logger.error(f"获取事件统计失败: {e}")
            return {"stats": ""}


# 全局单例
analytics_service = AnalyticsService()
