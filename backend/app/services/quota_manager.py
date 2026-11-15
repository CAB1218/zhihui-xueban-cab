"""
智慧学伴 多租户配额管理器
基于 Redis 的实时 token 计数 + PostgreSQL 配额配置

Redis Key 设计:
  quota:{tenant_id}:daily:{YYYY-MM-DD}      → int (日 token 用量), TTL 25h
  quota:{tenant_id}:monthly:{YYYY-MM}       → int (月 token 用量), TTL 35d
  quota:{tenant_id}:daily_req:{YYYY-MM-DD}  → int (日请求次数), TTL 25h
"""
import logging
from datetime import date
from typing import Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.redis import get_redis_client
from app.models.usage import LLMUsageLog, TenantQuota

logger = logging.getLogger(__name__)


class QuotaManager:
    """基于 Redis 的多租户配额管理器

    功能:
    - check_quota(): 检查租户配额是否充足
    - record_usage(): 记录一次 LLM 调用的用量（Redis INCRBY + 异步写 DB 日志）
    - get_usage(): 获取租户当前用量
    - get_tenant_strategy(): 从 DB 读取租户负载均衡策略
    """

    def __init__(self):
        self._redis = None  # 延迟初始化

    async def _get_redis(self):
        """获取 Redis 客户端（延迟初始化）"""
        if self._redis is None:
            self._redis = await get_redis_client()
        return self._redis

    def _daily_key(self, tenant_id: int) -> str:
        """生成日 token 计数 key"""
        today = date.today().isoformat()
        return f"{settings.QUOTA_REDIS_KEY_PREFIX}:{tenant_id}:daily:{today}"

    def _monthly_key(self, tenant_id: int) -> str:
        """生成月 token 计数 key"""
        year_month = date.today().strftime("%Y-%m")
        return f"{settings.QUOTA_REDIS_KEY_PREFIX}:{tenant_id}:monthly:{year_month}"

    def _daily_req_key(self, tenant_id: int) -> str:
        """生成日请求次数 key"""
        today = date.today().isoformat()
        return f"{settings.QUOTA_REDIS_KEY_PREFIX}:{tenant_id}:daily_req:{today}"

    async def _get_quota_config(self, tenant_id: int, db: AsyncSession = None) -> TenantQuota:
        """从 DB 读取租户配额配置，不存在则创建默认配置

        Args:
            tenant_id: 租户ID
            db: 数据库会话（可选，为 None 时不创建新配置）

        Returns:
            TenantQuota 实例（可能为 None）
        """
        if db is None:
            return None

        stmt = select(TenantQuota).where(TenantQuota.tenant_id == tenant_id)
        result = await db.execute(stmt)
        quota = result.scalars().first()

        if quota is None and db is not None:
            # 创建默认配额配置
            quota = TenantQuota(
                tenant_id=tenant_id,
                daily_token_limit=settings.QUOTA_DEFAULT_DAILY_TOKENS,
                monthly_token_limit=settings.QUOTA_DEFAULT_MONTHLY_TOKENS,
                strategy=settings.LLM_BALANCER_STRATEGY,
                is_active=True,
            )
            db.add(quota)
            await db.flush()

        return quota

    async def check_quota(
        self,
        tenant_id: int,
        estimated_tokens: int = 1000,
        db: AsyncSession = None,
    ) -> Tuple[bool, str]:
        """检查租户配额是否充足

        Args:
            tenant_id: 租户ID
            estimated_tokens: 预估本次调用的 token 数
            db: 数据库会话

        Returns:
            (is_allowed, reason): 允许返回 (True, "ok")；拒绝返回 (False, "daily_limit_exceeded" 等)
        """
        if not tenant_id:
            return True, "ok"  # 无租户信息时不拦截

        try:
            redis = await self._get_redis()

            # 读取 Redis 中的当前用量
            daily_used = int(await redis.get(self._daily_key(tenant_id)) or 0)
            monthly_used = int(await redis.get(self._monthly_key(tenant_id)) or 0)

            # 读取 DB 中的配额限制
            quota = await self._get_quota_config(tenant_id, db)
            if quota is None or not quota.is_active:
                # 无配置则使用默认值
                daily_limit = settings.QUOTA_DEFAULT_DAILY_TOKENS
                monthly_limit = settings.QUOTA_DEFAULT_MONTHLY_TOKENS
            else:
                daily_limit = quota.daily_token_limit
                monthly_limit = quota.monthly_token_limit

            # 检查日配额
            if daily_used + estimated_tokens > daily_limit:
                logger.warning(
                    "租户 %s 日配额超限: used=%d + est=%d > limit=%d",
                    tenant_id, daily_used, estimated_tokens, daily_limit,
                )
                return False, "daily_limit_exceeded"

            # 检查月配额
            if monthly_used + estimated_tokens > monthly_limit:
                logger.warning(
                    "租户 %s 月配额超限: used=%d + est=%d > limit=%d",
                    tenant_id, monthly_used, estimated_tokens, monthly_limit,
                )
                return False, "monthly_limit_exceeded"

            return True, "ok"

        except Exception as e:
            logger.error("配额检查异常（放行）: %s", e)
            # 异常时放行，避免影响正常使用
            return True, "ok"

    async def record_usage(
        self,
        tenant_id: int,
        tokens: int,
        provider: str,
        model_name: str,
        session_id: Optional[int] = None,
        user_id: Optional[int] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        status: str = "success",
        db: AsyncSession = None,
    ) -> None:
        """记录一次 LLM 调用的用量

        Redis INCRBY 更新日/月计数 + 异步写 DB 日志

        Args:
            tenant_id: 租户ID
            tokens: 总 token 数
            provider: 模型提供商
            model_name: 模型名称
            session_id: 会话ID
            user_id: 用户ID
            input_tokens: 输入 token
            output_tokens: 输出 token
            latency_ms: 延迟毫秒
            status: 状态 (success/failed/quota_exceeded)
            db: 数据库会话
        """
        if not tenant_id:
            return

        try:
            redis = await self._get_redis()

            # Redis INCRBY 更新 token 计数
            if tokens > 0:
                daily_key = self._daily_key(tenant_id)
                monthly_key = self._monthly_key(tenant_id)

                await redis.incrby(daily_key, tokens)
                await redis.expire(daily_key, settings.QUOTA_DAILY_TTL)

                await redis.incrby(monthly_key, tokens)
                await redis.expire(monthly_key, settings.QUOTA_MONTHLY_TTL)

            # 请求次数计数
            req_key = self._daily_req_key(tenant_id)
            await redis.incrby(req_key, 1)
            await redis.expire(req_key, settings.QUOTA_DAILY_TTL)

        except Exception as e:
            logger.error("Redis 配额计数失败: %s", e)

        # 异步写 DB 日志（不影响主流程）
        try:
            if db is not None:
                log = LLMUsageLog(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    session_id=session_id,
                    provider=provider,
                    model_name=model_name,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=tokens,
                    latency_ms=latency_ms,
                    status=status,
                )
                db.add(log)
                await db.flush()
        except Exception as e:
            logger.error("DB 用量日志写入失败: %s", e)

    async def get_usage(self, tenant_id: int, db: AsyncSession = None) -> dict:
        """获取租户当前用量

        Returns:
            {"daily_used": int, "daily_limit": int, "monthly_used": int, "monthly_limit": int,
             "daily_req_count": int, "usage_percentage": float}
        """
        if not tenant_id:
            return {
                "daily_used": 0, "daily_limit": settings.QUOTA_DEFAULT_DAILY_TOKENS,
                "monthly_used": 0, "monthly_limit": settings.QUOTA_DEFAULT_MONTHLY_TOKENS,
                "daily_req_count": 0, "usage_percentage": 0.0,
            }

        try:
            redis = await self._get_redis()

            daily_used = int(await redis.get(self._daily_key(tenant_id)) or 0)
            monthly_used = int(await redis.get(self._monthly_key(tenant_id)) or 0)
            daily_req = int(await redis.get(self._daily_req_key(tenant_id)) or 0)

            # 读取限额
            quota = await self._get_quota_config(tenant_id, db)
            if quota:
                daily_limit = quota.daily_token_limit
                monthly_limit = quota.monthly_token_limit
            else:
                daily_limit = settings.QUOTA_DEFAULT_DAILY_TOKENS
                monthly_limit = settings.QUOTA_DEFAULT_MONTHLY_TOKENS

            usage_pct = round(daily_used / daily_limit * 100, 2) if daily_limit > 0 else 0.0

            return {
                "daily_used": daily_used,
                "daily_limit": daily_limit,
                "monthly_used": monthly_used,
                "monthly_limit": monthly_limit,
                "daily_req_count": daily_req,
                "usage_percentage": usage_pct,
            }
        except Exception as e:
            logger.error("获取用量失败: %s", e)
            return {
                "daily_used": 0, "daily_limit": settings.QUOTA_DEFAULT_DAILY_TOKENS,
                "monthly_used": 0, "monthly_limit": settings.QUOTA_DEFAULT_MONTHLY_TOKENS,
                "daily_req_count": 0, "usage_percentage": 0.0,
            }

    async def get_tenant_strategy(self, tenant_id: int, db: AsyncSession) -> str:
        """从 DB 读取租户负载均衡策略

        Returns:
            策略字符串: latency / weighted / sticky
        """
        if not tenant_id:
            return settings.LLM_BALANCER_STRATEGY

        try:
            quota = await self._get_quota_config(tenant_id, db)
            if quota and quota.strategy:
                return quota.strategy
        except Exception as e:
            logger.error("读取租户策略失败: %s", e)

        return settings.LLM_BALANCER_STRATEGY


# 全局单例
quota_manager = QuotaManager()
