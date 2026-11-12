"""
AI4Edu FastAPI 应用入口
注册中间件、路由、生命周期事件
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.exceptions import AppException, app_exception_handler
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.tenant import TenantMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.api.v1.router import api_v1_router

# 确保所有 ORM 模型在应用启动时注册到 Base.metadata
# 这样 SQLAlchemy 才能正确解析外键引用
import app.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    import structlog
    logger = structlog.get_logger()
    logger.info("ai4edu_backend_starting", env=settings.APP_ENV)

    # 初始化数据库连接池（SQLAlchemy async engine 已在 database.py 模块级创建）

    # 初始化 Redis 连接
    try:
        from app.core.redis import get_redis_client, close_redis
        await get_redis_client()
        logger.info("redis_connected")
    except Exception as e:
        logger.warning("redis_connection_failed", error=str(e))

    # 初始化 Neo4j 连接
    try:
        from app.services.graph_service import graph_service
        await graph_service._get_driver()
        logger.info("neo4j_connected")
    except Exception as e:
        logger.warning("neo4j_connection_failed", error=str(e))

    # 初始化 OpenTelemetry
    try:
        from app.core.telemetry import setup_telemetry
        setup_telemetry()
        logger.info("otel_initialized")
    except Exception as e:
        logger.warning("otel_init_failed", error=str(e))

    # 加载「AI 对话 → 模型配置」里保存的 API Key / Base / 模型名
    # 页面配置优先于 backend/.env，加载后模型路由器立即可用
    try:
        from app.database import async_session_factory
        from app.services import llm_config_service

        async with async_session_factory() as session:
            overrides = await llm_config_service.apply_to_router(session)
        logger.info("llm_config_loaded", providers=list(overrides.keys()))
    except Exception as e:
        logger.warning("llm_config_load_failed", error=str(e))

    yield

    # 关闭事件
    logger.info("ai4edu_backend_stopping")

    # 关闭 Redis 连接
    try:
        from app.core.redis import close_redis
        await close_redis()
    except Exception:
        pass

    # 关闭数据库连接池
    from app.database import engine
    await engine.dispose()
    logger.info("database_disposed")


app = FastAPI(
    title=settings.APP_NAME,
    description="智慧学伴智能体 API（AI 驱动的个性化学习与智慧教学平台）",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ============ 中间件注册（顺序重要：后注册先执行） ============

# CORS 中间件 — 开发/演示环境允许所有来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 演示环境允许所有来源（含 cloudflared/ngrok 隧道）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# 请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 限流中间件
app.add_middleware(RateLimitMiddleware)

# 租户识别中间件
app.add_middleware(TenantMiddleware)

# ============ 异常处理器注册 ============

app.add_exception_handler(AppException, app_exception_handler)

# ============ 路由注册 ============

app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["健康检查"])
async def health_check():
    """服务健康检查端点"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "env": settings.APP_ENV,
    }


@app.get("/", tags=["根路径"])
async def root():
    """API根路径"""
    return {
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "docs": "/docs",
    }
