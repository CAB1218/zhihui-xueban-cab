"""
智慧学伴 后端配置管理模块
使用 Pydantic Settings 从环境变量加载配置
"""
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用全局配置"""

    # 应用配置
    APP_NAME: str = "ai4edu"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"
    API_V1_PREFIX: str = "/api/v1"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ai4edu"
    POSTGRES_USER: str = "ai4edu"
    POSTGRES_PASSWORD: str = "ai4edu_password"

    @property
    def DATABASE_URL(self) -> str:
        """异步数据库连接URL"""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        """同步数据库连接URL（Alembic迁移用）"""
        return (
            f"postgresql+pg8000://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Neo4j
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "neo4j_password"

    # ClickHouse
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 9000
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = "clickhouse_password"

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        """Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ai4edu"
    MINIO_SECURE: bool = False
    MINIO_PUBLIC_ENDPOINT: str = ""  # 浏览器可访问的 MinIO 地址，留空则回退到 MINIO_ENDPOINT

    @property
    def MINIO_PUBLIC_ENDPOINT_OR_DEFAULT(self) -> str:
        """浏览器可访问的 MinIO 地址（留空回退到 MINIO_ENDPOINT）

        用于生成返回给前端/浏览器的预签名下载 URL。
        在 Docker 部署中，MINIO_ENDPOINT 通常为内网地址（如 minio:9000），
        而浏览器无法解析该 hostname，因此需要通过 MINIO_PUBLIC_ENDPOINT
        指定一个外部可访问的地址（如 121.43.129.181:9002）。
        """
        return self.MINIO_PUBLIC_ENDPOINT or self.MINIO_ENDPOINT

    # Elasticsearch
    ELASTICSEARCH_HOST: str = "http://localhost:9200"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时，演示环境延长
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """解析 CORS 配置，支持逗号分隔的字符串"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4o"

    # ============ 多模型配置 ============
    # 多模型路由开关（false 时回退到单一 OPENAI_* 配置）
    LLM_MULTI_MODEL_ENABLED: bool = True

    # DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 腾讯混元（OpenAI 兼容模式）
    HUNYUAN_API_KEY: str = ""
    HUNYUAN_API_BASE: str = "https://api.hunyuan.cloud.tencent.com/v1"
    HUNYUAN_MODEL: str = "hunyuan-pro"

    # 阿里通义千问（DashScope OpenAI 兼容模式）
    QWEN_API_KEY: str = ""
    QWEN_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    # 模型优先级（逗号分隔，从高到低）
    LLM_MODEL_PRIORITY: str = "deepseek,qwen,hunyuan"

    # 单模型连续失败次数阈值（超过后切换备选）
    LLM_MAX_FAILURES: int = 2

    # 速率限制（每分钟最大请求数，0=不限制）
    LLM_RATE_LIMIT_PER_MINUTE: int = 60

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ============ v2 新增：Celery beat 配置 ============
    CELERY_BEAT_HEALTH_CHECK_INTERVAL: int = 60  # 模型健康检查间隔（秒）

    # ============ v2 新增：OCR/ASR 配置 ============
    ALIYUN_OCR_API_KEY: str = ""
    ALIYUN_OCR_ENDPOINT: str = "https://ocr-api.cn-hangzhou.aliyuncs.com"
    ALIYUN_ASR_APP_KEY: str = ""
    ALIYUN_ASR_ENDPOINT: str = "https://nls-meta.cn-shanghai.aliyuncs.com"
    TENCENT_OCR_SECRET_ID: str = ""
    TENCENT_OCR_SECRET_KEY: str = ""
    TENCENT_OCR_REGION: str = "ap-guangzhou"
    TENCENT_ASR_SECRET_ID: str = ""
    TENCENT_ASR_SECRET_KEY: str = ""
    TENCENT_ASR_REGION: str = "ap-guangzhou"
    OCR_PROVIDER_PRIORITY: str = "aliyun,tencent,mock"  # 逗号分隔

    # ============ v2 新增：负载均衡配置 ============
    LLM_BALANCER_STRATEGY: str = "latency"  # latency / weighted / sticky
    LLM_STICKY_DEFAULT: bool = False  # sticky 默认关闭
    LLM_HEALTH_CHECK_TIMEOUT: int = 10  # 健康检查超时秒数

    # ============ v2 新增：导出配置 ============
    EXPORT_MINIO_BUCKET: str = "ai4edu-exports"
    EXPORT_PRESIGN_EXPIRE: int = 1800  # 预签名 URL 有效期秒数（30min）
    EXPORT_MAX_FILE_SIZE: int = 104857600  # 上传文件最大 100MB

    # ============ v2 新增：配额配置 ============
    QUOTA_DEFAULT_DAILY_TOKENS: int = 500000
    QUOTA_DEFAULT_MONTHLY_TOKENS: int = 10000000
    QUOTA_REDIS_KEY_PREFIX: str = "quota"
    QUOTA_DAILY_TTL: int = 90000       # 25h in seconds
    QUOTA_MONTHLY_TTL: int = 3024000   # 35d in seconds

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "ai4edu-backend"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


# 全局配置单例
settings = Settings()
