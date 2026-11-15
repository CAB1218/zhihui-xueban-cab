"""
智慧学伴 分析事件 ORM 模型
ClickHouse 事件表
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AnalyticsEvent(Base):
    """分析事件表 - ClickHouse，不在 PostgreSQL 中创建"""

    __tablename__ = "analytics_events"
    __table_args__ = {"schema": "clickhouse"}  # 标记为 ClickHouse 表，Alembic autogenerate 会忽略不同 schema

    id: Mapped[str] = mapped_column(String(36), primary_key=True, comment="事件UUID")
    user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="用户ID")
    tenant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="租户ID")
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="事件类型")
    event_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="事件数据JSON")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, comment="事件时间"
    )


# 事件类型枚举
class EventType:
    """8种事件类型"""

    PAGE_VIEW = "page_view"  # 页面浏览
    RESOURCE_UPLOAD = "resource_upload"  # 资源上传
    RESOURCE_DOWNLOAD = "resource_download"  # 资源下载
    SEARCH_QUERY = "search_query"  # 搜索查询
    GRAPH_BROWSE = "graph_browse"  # 图谱浏览
    NODE_CLICK = "node_click"  # 知识点点击
    AI_CHAT = "ai_chat"  # AI对话
    SCENE_SWITCH = "scene_switch"  # 场景切换
