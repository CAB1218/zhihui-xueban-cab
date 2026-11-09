"""
AI4Edu 基础设施业务初始化脚本
初始化 ClickHouse / MinIO / Elasticsearch 的业务数据结构
"""
import json
import logging
import os
import sys

import httpx

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# 基础设施配置 — 优先读环境变量，容器内由 docker-compose 注入
CLICKHOUSE_HOST = os.getenv("CLICKHOUSE_HOST", "localhost")
CLICKHOUSE_HTTP_PORT = 8123
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "default")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse_password")
CLICKHOUSE_DB = "ai4edu"

ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9002")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")


# ==================== ClickHouse 初始化 ====================

def init_clickhouse():
    """初始化 ClickHouse：创建数据库和事件表"""
    logger.info("=" * 50)
    logger.info("开始初始化 ClickHouse")

    base_url = f"http://{CLICKHOUSE_HOST}:{CLICKHOUSE_HTTP_PORT}"
    params = {"user": CLICKHOUSE_USER, "password": CLICKHOUSE_PASSWORD}

    with httpx.Client(timeout=30) as client:
        # 1. 创建数据库
        try:
            resp = client.post(
                base_url,
                params=params,
                content=f"CREATE DATABASE IF NOT EXISTS {CLICKHOUSE_DB}",
            )
            if resp.status_code == 200:
                logger.info(f"  数据库 '{CLICKHOUSE_DB}' 创建成功（或已存在）")
            else:
                logger.error(f"  创建数据库失败: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"  创建数据库异常: {e}")
            return False

        # 2. 创建 analytics_events 表（MergeTree 引擎）
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {CLICKHOUSE_DB}.analytics_events (
            id String COMMENT '事件UUID',
            user_id Nullable(Int32) COMMENT '用户ID',
            tenant_id Nullable(Int32) COMMENT '租户ID',
            event_type String COMMENT '事件类型',
            event_data Nullable(String) COMMENT '事件数据JSON',
            timestamp DateTime COMMENT '事件时间'
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(timestamp)
        ORDER BY (event_type, timestamp)
        TTL timestamp + INTERVAL 180 DAY
        SETTINGS index_granularity = 8192
        """
        try:
            resp = client.post(base_url, params=params, content=create_table_sql)
            if resp.status_code == 200:
                logger.info("  analytics_events 表创建成功（或已存在）")
            else:
                logger.error(f"  创建表失败: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            logger.error(f"  创建表异常: {e}")
            return False

        # 3. 创建 event_type 索引物化视图（加速按类型查询）
        mv_sql = f"""
        CREATE MATERIALIZED VIEW IF NOT EXISTS {CLICKHOUSE_DB}.mv_event_type_stats
        ENGINE = SummingMergeTree()
        PARTITION BY toYYYYMM(hour)
        ORDER BY (event_type, hour)
        AS SELECT
            event_type,
            toStartOfHour(timestamp) AS hour,
            count() AS event_count
        FROM {CLICKHOUSE_DB}.analytics_events
        GROUP BY event_type, toStartOfHour(timestamp)
        """
        try:
            resp = client.post(base_url, params=params, content=mv_sql)
            if resp.status_code == 200:
                logger.info("  mv_event_type_stats 物化视图创建成功（或已存在）")
            else:
                logger.warning(f"  物化视图创建失败（非关键）: {resp.status_code} {resp.text}")
        except Exception as e:
            logger.warning(f"  物化视图创建异常（非关键）: {e}")

        # 4. 验证表结构
        try:
            resp = client.post(
                base_url,
                params={**params, "database": CLICKHOUSE_DB},
                content="DESCRIBE analytics_events",
            )
            if resp.status_code == 200:
                logger.info("  表结构验证:")
                for line in resp.text.strip().split("\n"):
                    logger.info(f"    {line}")
            else:
                logger.warning(f"  验证表结构失败: {resp.status_code}")
        except Exception as e:
            logger.warning(f"  验证表结构异常: {e}")

    logger.info("ClickHouse 初始化完成 ✓")
    return True


# ==================== Elasticsearch 初始化 ====================

def init_elasticsearch():
    """初始化 Elasticsearch：创建索引和映射"""
    logger.info("=" * 50)
    logger.info("开始初始化 Elasticsearch")

    # ai4edu 主索引映射（资源+知识节点）
    ai4edu_mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "ik_smart_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"],
                    },
                    "ik_max_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase"],
                    },
                },
            },
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {
                        "keyword": {"type": "keyword"},
                        "suggest": {"type": "completion"},
                    },
                },
                "content": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "description": {
                    "type": "text",
                    "analyzer": "standard",
                },
                "tags": {
                    "type": "text",
                    "analyzer": "standard",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "doc_type": {
                    "type": "keyword",
                },
                "type": {
                    "type": "keyword",
                },
                "tenant_id": {
                    "type": "integer",
                },
                "created_at": {
                    "type": "date",
                    "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd'T'HH:mm:ss||epoch_millis",
                },
                "updated_at": {
                    "type": "date",
                    "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd'T'HH:mm:ss||epoch_millis",
                },
                "resource_type": {"type": "keyword"},
                "file_size": {"type": "long"},
                "subject": {"type": "keyword"},
                "difficulty": {"type": "keyword"},
            },
        },
    }

    # 搜索日志索引
    search_logs_mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "query_keyword": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword"}},
                },
                "user_id": {"type": "integer"},
                "tenant_id": {"type": "integer"},
                "result_count": {"type": "integer"},
                "timestamp": {
                    "type": "date",
                    "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd'T'HH:mm:ss||epoch_millis",
                },
            },
        },
    }

    with httpx.Client(timeout=30) as client:
        # 1. 创建主索引
        try:
            # 先检查索引是否已存在
            resp = client.get(f"{ELASTICSEARCH_HOST}/ai4edu")
            if resp.status_code == 200:
                logger.info("  索引 'ai4edu' 已存在，跳过创建")
            else:
                resp = client.put(
                    f"{ELASTICSEARCH_HOST}/ai4edu",
                    json=ai4edu_mapping,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code in (200, 201):
                    logger.info("  索引 'ai4edu' 创建成功")
                else:
                    logger.error(f"  创建索引失败: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"  创建索引异常: {e}")
            return False

        # 2. 创建搜索日志索引
        try:
            resp = client.get(f"{ELASTICSEARCH_HOST}/ai4edu_search_logs")
            if resp.status_code == 200:
                logger.info("  索引 'ai4edu_search_logs' 已存在，跳过创建")
            else:
                resp = client.put(
                    f"{ELASTICSEARCH_HOST}/ai4edu_search_logs",
                    json=search_logs_mapping,
                    headers={"Content-Type": "application/json"},
                )
                if resp.status_code in (200, 201):
                    logger.info("  索引 'ai4edu_search_logs' 创建成功")
                else:
                    logger.error(f"  创建搜索日志索引失败: {resp.status_code} {resp.text}")
                    return False
        except Exception as e:
            logger.error(f"  创建搜索日志索引异常: {e}")
            return False

        # 3. 验证索引
        try:
            resp = client.get(f"{ELASTICSEARCH_HOST}/_cat/indices?v&format=json")
            if resp.status_code == 200:
                indices = resp.json()
                ai4edu_indices = [i for i in indices if i.get("index", "").startswith("ai4edu")]
                logger.info(f"  当前 ai4edu 相关索引: {[i['index'] for i in ai4edu_indices]}")
        except Exception as e:
            logger.warning(f"  验证索引异常: {e}")

    logger.info("Elasticsearch 初始化完成 ✓")
    return True


# ==================== MinIO 初始化 ====================

def init_minio():
    """初始化 MinIO：创建 bucket 和策略"""
    logger.info("=" * 50)
    logger.info("开始初始化 MinIO")

    try:
        from minio import Minio
        from minio.error import S3Error

        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )

        # 1. 创建主 bucket
        bucket_name = "ai4edu"
        try:
            if client.bucket_exists(bucket_name):
                logger.info(f"  Bucket '{bucket_name}' 已存在")
            else:
                client.make_bucket(bucket_name)
                logger.info(f"  Bucket '{bucket_name}' 创建成功")
        except S3Error as e:
            logger.error(f"  创建 Bucket 失败: {e}")
            return False

        # 2. 创建资源子目录 bucket
        sub_buckets = ["ai4edu-resources", "ai4edu-avatars", "ai4edu-temp"]
        for sb in sub_buckets:
            try:
                if client.bucket_exists(sb):
                    logger.info(f"  Bucket '{sb}' 已存在")
                else:
                    client.make_bucket(sb)
                    logger.info(f"  Bucket '{sb}' 创建成功")
            except S3Error as e:
                logger.warning(f"  创建 Bucket '{sb}' 失败（非关键）: {e}")

        # 3. 设置 bucket 策略（允许公开读取 avatars）
        avatar_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "*"},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::ai4edu-avatars/*"],
                }
            ],
        }
        try:
            client.set_bucket_policy("ai4edu-avatars", json.dumps(avatar_policy))
            logger.info("  ai4edu-avatars 公开读取策略设置成功")
        except S3Error as e:
            logger.warning(f"  设置 avatars 策略失败（非关键）: {e}")

        # 4. 验证
        try:
            buckets = client.list_buckets()
            ai4edu_buckets = [b.name for b in buckets if b.name.startswith("ai4edu")]
            logger.info(f"  当前 ai4edu 相关 Buckets: {ai4edu_buckets}")
        except S3Error as e:
            logger.warning(f"  验证 Buckets 异常: {e}")

    except ImportError:
        logger.error("  minio 包未安装，请运行: pip install minio")
        return False
    except Exception as e:
        logger.error(f"  MinIO 初始化异常: {e}")
        return False

    logger.info("MinIO 初始化完成 ✓")
    return True


# ==================== 主入口 ====================

def main():
    logger.info("AI4Edu 基础设施业务初始化")
    logger.info("=" * 50)

    results = {}

    # ClickHouse
    results["clickhouse"] = init_clickhouse()

    # Elasticsearch
    results["elasticsearch"] = init_elasticsearch()

    # MinIO
    results["minio"] = init_minio()

    # 汇总
    logger.info("=" * 50)
    logger.info("初始化结果汇总:")
    all_ok = True
    for svc, ok in results.items():
        status = "✓ 成功" if ok else "✗ 失败"
        logger.info(f"  {svc}: {status}")
        if not ok:
            all_ok = False

    if all_ok:
        logger.info("所有基础设施初始化完成！")
    else:
        logger.warning("部分基础设施初始化失败，请检查日志")
        sys.exit(1)


if __name__ == "__main__":
    main()
