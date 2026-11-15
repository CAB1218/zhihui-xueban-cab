"""
智慧学伴 Celery 应用实例
提供异步任务队列 + Beat 定时调度（模型健康检查每 60s 执行）

启动 Worker: celery -A app.core.celery_app worker -l info
启动 Beat:   celery -A app.core.celery_app beat -l info
"""
import logging

from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# Celery 应用实例
celery_app = Celery(
    "ai4edu",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,           # 单任务最大 10 分钟
    task_soft_time_limit=540,      # 软超时 9 分钟
    worker_prefetch_multiplier=1,  # 一次只取一个任务，避免长任务阻塞
    # Beat 调度
    beat_schedule={
        "model-health-check": {
            "task": "app.tasks.health_check.health_check_task",
            "schedule": float(settings.CELERY_BEAT_HEALTH_CHECK_INTERVAL),
        },
    },
)

# 同步数据库引擎（Celery worker 是同步进程，不能使用 asyncpg）
_sync_engine = None
_SyncSessionLocal = None


def get_sync_engine():
    """获取同步数据库引擎（懒加载单例）"""
    global _sync_engine, _SyncSessionLocal
    if _sync_engine is None:
        sync_url = settings.DATABASE_URL_SYNC
        _sync_engine = create_engine(
            sync_url,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        _SyncSessionLocal = sessionmaker(bind=_sync_engine, expire_on_commit=False)
        logger.info("Celery 同步数据库引擎已初始化: %s", sync_url.split("@")[-1])
    return _sync_engine


def get_sync_session():
    """获取同步数据库 Session"""
    if _SyncSessionLocal is None:
        get_sync_engine()
    return _SyncSessionLocal()


# 自动发现任务模块
celery_app.autodiscover_tasks(["app.tasks"])
