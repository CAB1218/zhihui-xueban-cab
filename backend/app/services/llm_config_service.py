"""
大模型服务商配置服务

职责：
1. 读取/保存「页面配置」（llm_provider_configs），与 backend/.env 的默认值合并成有效配置
2. 把有效配置推给 llm_router，保存后立即生效（不用重启后端）
3. 提供连通性测试：真正发一次最小 chat/completions 请求，区分「填了 Key」与「Key 真的能用」

安全：
- API Key 用 app.core.encryption.encrypt_field 加密入库，接口只返回掩码（sk-****abcd）
- 明文只在测试连接时短暂使用，不写日志
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.encryption import decrypt_field, encrypt_field
from app.models.llm_config import LlmProviderConfig

logger = logging.getLogger(__name__)

# 三个服务商的展示信息与默认值来源
PROVIDER_META: Dict[str, Dict[str, Any]] = {
    "deepseek": {
        "label": "DeepSeek",
        "key_url": "https://platform.deepseek.com/api_keys",
        "hint": "DeepSeek 开放平台创建 API Key（sk- 开头），余额不足会返回 402",
    },
    "qwen": {
        "label": "通义千问",
        "key_url": "https://bailian.console.aliyun.com/",
        "hint": "阿里云百炼控制台创建 API Key，兼容 OpenAI 协议",
    },
    "hunyuan": {
        "label": "腾讯混元",
        "key_url": "https://console.cloud.tencent.com/hunyuan",
        "hint": "腾讯云混元控制台创建 API Key，兼容 OpenAI 协议",
    },
}

PROVIDER_ORDER = ["deepseek", "qwen", "hunyuan"]

# 明显是占位符的 Key 不算已配置（与 llm_router.ModelProvider.is_configured 保持一致）
_PLACEHOLDER_KEYS = {"", "sk-xxx", "xxx", "sk-your-openai-api-key"}


def _env_defaults(provider: str) -> Dict[str, str]:
    """backend/.env 里的默认值"""
    if provider == "deepseek":
        return {
            "api_key": settings.DEEPSEEK_API_KEY or "",
            "api_base": settings.DEEPSEEK_API_BASE or "https://api.deepseek.com/v1",
            "model_name": settings.DEEPSEEK_MODEL or "deepseek-chat",
        }
    if provider == "qwen":
        return {
            "api_key": settings.QWEN_API_KEY or "",
            "api_base": settings.QWEN_API_BASE or "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "model_name": settings.QWEN_MODEL or "qwen-plus",
        }
    if provider == "hunyuan":
        return {
            "api_key": settings.HUNYUAN_API_KEY or "",
            "api_base": settings.HUNYUAN_API_BASE or "https://api.hunyuan.cloud.tencent.com/v1",
            "model_name": settings.HUNYUAN_MODEL or "hunyuan-pro",
        }
    return {"api_key": "", "api_base": "", "model_name": ""}


def _is_real_key(key: Optional[str]) -> bool:
    return bool(key) and key.strip() not in _PLACEHOLDER_KEYS


def mask_key(key: Optional[str]) -> str:
    """sk-abcd****wxyz —— 只用于回显，绝不返回明文"""
    if not key:
        return ""
    key = key.strip()
    if len(key) <= 8:
        return "****"
    return f"{key[:5]}****{key[-4:]}"


def normalize_base(url: Optional[str]) -> str:
    """统一去掉尾部斜杠，避免拼出 //chat/completions"""
    return (url or "").strip().rstrip("/")


async def _get_row(db: AsyncSession, provider: str) -> Optional[LlmProviderConfig]:
    result = await db.execute(
        select(LlmProviderConfig).where(LlmProviderConfig.provider == provider)
    )
    return result.scalars().first()


def _row_key(row: Optional[LlmProviderConfig]) -> str:
    if row is None or not row.api_key_encrypted:
        return ""
    try:
        return decrypt_field(row.api_key_encrypted)
    except Exception as e:  # noqa: BLE001 — SECRET_KEY 变了会解不开，不应导致接口 500
        logger.warning("解密 %s 的 API Key 失败: %s", row.provider if row else "?", e)
        return ""


async def load_overrides(db: AsyncSession) -> Dict[str, Dict[str, str]]:
    """从数据库读出所有页面覆盖配置（含解密后的 Key），供 llm_router 使用"""
    rows = (await db.execute(select(LlmProviderConfig))).scalars().all()
    overrides: Dict[str, Dict[str, str]] = {}
    for row in rows:
        cfg: Dict[str, str] = {}
        key = _row_key(row)
        if key:
            cfg["api_key"] = key
        if row.api_base:
            cfg["api_base"] = row.api_base
        if row.model_name:
            cfg["model_name"] = row.model_name
        if cfg:
            overrides[row.provider] = cfg
    return overrides


async def apply_to_router(db: AsyncSession) -> Dict[str, Dict[str, str]]:
    """把页面配置推到全局 llm_router，立即生效"""
    from app.agents.llm_router import llm_router

    overrides = await load_overrides(db)
    await llm_router.apply_overrides(overrides)
    return overrides


async def effective_secrets(db: AsyncSession, provider: str) -> Dict[str, str]:
    """当前生效的明文配置（页面配置优先，其次 .env），仅供服务端内部使用"""
    env = _env_defaults(provider)
    row = await _get_row(db, provider)
    key = _row_key(row)
    if not key and _is_real_key(env["api_key"]):
        key = env["api_key"]
    return {
        "api_key": key,
        "api_base": (row.api_base if row and row.api_base else env["api_base"]),
        "model_name": (row.model_name if row and row.model_name else env["model_name"]),
    }


async def describe_providers(db: AsyncSession) -> List[Dict[str, Any]]:
    """界面用的服务商配置清单（Key 只给掩码）"""
    rows = {
        row.provider: row
        for row in (await db.execute(select(LlmProviderConfig))).scalars().all()
    }
    items: List[Dict[str, Any]] = []
    for provider in PROVIDER_ORDER:
        meta = PROVIDER_META[provider]
        env = _env_defaults(provider)
        row = rows.get(provider)
        db_key = _row_key(row)
        # 页面配置优先，其次 .env
        if db_key:
            api_key, source = db_key, "page"
        elif _is_real_key(env["api_key"]):
            api_key, source = env["api_key"], "env"
        else:
            api_key, source = "", "none"

        items.append(
            {
                "provider": provider,
                "label": meta["label"],
                "key_url": meta["key_url"],
                "hint": meta["hint"],
                "api_base": (row.api_base if row and row.api_base else env["api_base"]),
                "model_name": (row.model_name if row and row.model_name else env["model_name"]),
                "has_key": bool(api_key),
                "key_masked": mask_key(api_key),
                "configured": _is_real_key(api_key),
                "source": source,  # page / env / none
                "editable_key": bool(db_key),  # 页面上是否已有可清除的 Key
                "env_key_masked": mask_key(env["api_key"]) if _is_real_key(env["api_key"]) else "",
                "last_test_ok": row.last_test_ok if row else None,
                "last_test_message": row.last_test_message if row else None,
                "last_test_at": row.last_test_at.isoformat() if row and row.last_test_at else None,
            }
        )
    return items


async def save_config(
    db: AsyncSession,
    provider: str,
    *,
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    model_name: Optional[str] = None,
    clear_key: bool = False,
    user_id: Optional[int] = None,
) -> None:
    """保存页面配置。api_key=None 表示「不改动」，clear_key=True 表示清除页面 Key 回到 .env"""
    if provider not in PROVIDER_META:
        raise ValueError(f"不支持的服务商: {provider}")

    row = await _get_row(db, provider)
    if row is None:
        row = LlmProviderConfig(provider=provider)
        db.add(row)

    if clear_key:
        row.api_key_encrypted = None
    elif api_key is not None:
        key = api_key.strip()
        row.api_key_encrypted = encrypt_field(key) if key else None

    if api_base is not None:
        row.api_base = normalize_base(api_base) or None
    if model_name is not None:
        row.model_name = (model_name or "").strip() or None

    # 配置变了，旧的测试结论作废
    row.last_test_ok = None
    row.last_test_message = None
    row.last_test_at = None
    row.updated_by = user_id

    await db.commit()
    await apply_to_router(db)


async def reset_config(db: AsyncSession, provider: str) -> None:
    """删除页面配置，回退到 backend/.env"""
    row = await _get_row(db, provider)
    if row is not None:
        await db.delete(row)
        await db.commit()
    await apply_to_router(db)


async def test_connection(
    provider: str,
    *,
    api_key: str,
    api_base: str,
    model_name: str,
) -> Dict[str, Any]:
    """真实发一次最小请求，验证 Key / Base / 模型名是否可用"""
    if provider not in PROVIDER_META:
        return {"ok": False, "message": f"不支持的服务商: {provider}", "latency_ms": None}

    if not _is_real_key(api_key):
        return {"ok": False, "message": "请先填写 API Key（sk- 开头）", "latency_ms": None}

    url = f"{normalize_base(api_base)}/chat/completions"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key.strip()}", "Content-Type": "application/json"}

    started = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
        latency = int((time.monotonic() - started) * 1000)

        if resp.status_code == 200:
            data = resp.json()
            model_echo = (data.get("model") or model_name) if isinstance(data, dict) else model_name
            usage = (data.get("usage") or {}) if isinstance(data, dict) else {}
            return {
                "ok": True,
                "message": f"连接成功（{model_echo}，返回 {usage.get('total_tokens', '?')} tokens）",
                "latency_ms": latency,
            }

        detail = ""
        try:
            body = resp.json()
            detail = (
                body.get("error", {}).get("message")
                or body.get("message")
                or str(body)[:200]
            )
        except Exception:  # noqa: BLE001 — 非 JSON 响应（网关错误页等）
            detail = (resp.text or "")[:200]

        hints = {
            401: "Key 无效或已过期",
            402: "账户余额不足",
            403: "Key 无权限访问该模型",
            404: "API Base 或模型名不存在",
            429: "触发限流，请稍后再试",
        }
        prefix = hints.get(resp.status_code, f"HTTP {resp.status_code}")
        return {
            "ok": False,
            "message": f"{prefix}：{detail}" if detail else prefix,
            "latency_ms": latency,
        }
    except httpx.TimeoutException:
        return {"ok": False, "message": "请求超时（25s），请检查网络或 API Base", "latency_ms": None}
    except httpx.HTTPError as e:
        return {"ok": False, "message": f"网络请求失败：{e}", "latency_ms": None}
    except Exception as e:  # noqa: BLE001
        logger.error("测试 %s 连接异常: %s", provider, e)
        return {"ok": False, "message": f"测试失败：{e}", "latency_ms": None}


async def record_test_result(
    db: AsyncSession, provider: str, ok: bool, message: str
) -> None:
    """把测试结论落库，界面据此区分「已配置」和「已验证可用」"""
    from datetime import datetime

    row = await _get_row(db, provider)
    if row is None:
        return
    row.last_test_ok = ok
    row.last_test_message = message[:500]
    row.last_test_at = datetime.utcnow()
    await db.commit()
