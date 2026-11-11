"""
AI4Edu 大模型服务商配置 API

端点（挂载在 /agents/models/config 下）：
    GET    /                     查看三家服务商的当前配置（Key 只回显掩码）
    PUT    /{provider}           保存 API Key / API Base / 模型名，立即生效
    DELETE /{provider}           清除页面配置，回退到 backend/.env
    POST   /{provider}/test      真实发一次最小请求，验证 Key 是否可用

权限：查看、修改、测试都对所有登录用户开放（配置页在 AI 对话里，谁用谁配）。
注意：配置是「全站共享」的一条记录，谁保存谁生效，前端会明确提示这一点。
若某天需要「每人用自己的 Key」，再按 user_id 拆分记录即可（表里已有 updated_by）。
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.common import APIResponse
from app.services import llm_config_service as svc

router = APIRouter()

def _ensure_active(user: User) -> None:
    """任何已登录且未被禁用的用户都可以配置模型（谁用谁配）"""
    if not user or not user.is_active:
        raise AppException(code=403, message="账号已被禁用，无法修改模型配置")


class LlmConfigUpdate(BaseModel):
    """保存配置：字段为 None 表示不改动"""

    api_key: Optional[str] = Field(None, description="API Key，留空且 clear_key=false 时不改动")
    api_base: Optional[str] = Field(None, description="API Base，如 https://api.deepseek.com/v1")
    model_name: Optional[str] = Field(None, description="模型名，如 deepseek-chat")
    clear_key: bool = Field(False, description="true 时清除页面上的 Key，回退到 .env")


class LlmTestRequest(BaseModel):
    """测试连接：三个字段都传时用页面上的临时值测试（不落库）"""

    api_key: Optional[str] = None
    api_base: Optional[str] = None
    model_name: Optional[str] = None


def _can_edit(user: User) -> bool:
    """所有人都可以编辑（配置是全局共享的，前端会提示影响范围）"""
    return bool(user and user.is_active)


async def _payload(db: AsyncSession, user: User) -> dict:
    providers = await svc.describe_providers(db)
    return {
        "providers": providers,
        "any_configured": any(p["configured"] for p in providers),
        "can_edit": _can_edit(user),
    }


@router.get("", summary="查看模型服务商配置")
async def get_model_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    return APIResponse(code=0, data=await _payload(db, current_user), message="success")


@router.put("/{provider}", summary="保存模型服务商配置")
async def save_model_config(
    provider: str,
    body: LlmConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    _ensure_active(current_user)
    if provider not in svc.PROVIDER_META:
        raise AppException(code=400, message=f"不支持的服务商: {provider}")

    # 只填了空格视为清空；Key 未传（None）表示沿用原值
    api_key = body.api_key
    if api_key is not None:
        api_key = api_key.strip()
        if api_key and any(ch.isspace() for ch in api_key):
            raise AppException(code=400, message="API Key 不能包含空格或换行")
        if api_key and provider == "deepseek" and not api_key.startswith("sk-"):
            raise AppException(code=400, message="DeepSeek 的 API Key 应以 sk- 开头")

    await svc.save_config(
        db,
        provider,
        api_key=api_key,
        api_base=body.api_base,
        model_name=body.model_name,
        clear_key=body.clear_key,
        user_id=current_user.id,
    )
    return APIResponse(code=0, data=await _payload(db, current_user), message="配置已保存并生效")


@router.delete("/{provider}", summary="清除页面配置，回退到 .env")
async def reset_model_config(
    provider: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    _ensure_active(current_user)
    if provider not in svc.PROVIDER_META:
        raise AppException(code=400, message=f"不支持的服务商: {provider}")
    await svc.reset_config(db, provider)
    return APIResponse(code=0, data=await _payload(db, current_user), message="已恢复为 .env 配置")


@router.post("/{provider}/test", summary="测试模型连通性")
async def test_model_connection(
    provider: str,
    body: Optional[LlmTestRequest] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> APIResponse:
    _ensure_active(current_user)
    if provider not in svc.PROVIDER_META:
        raise AppException(code=400, message=f"不支持的服务商: {provider}")

    current = await svc.effective_secrets(db, provider)
    body = body or LlmTestRequest()
    use_temp = bool(body.api_key) or bool(body.api_base) or bool(body.model_name)

    api_key = (body.api_key or "").strip() or current["api_key"]
    api_base = (body.api_base or "").strip() or current["api_base"]
    model_name = (body.model_name or "").strip() or current["model_name"]

    result = await svc.test_connection(
        provider, api_key=api_key, api_base=api_base, model_name=model_name
    )

    # 测试的是已保存的配置时，把结论记下来，界面可显示「已验证可用」
    if not use_temp:
        await svc.record_test_result(db, provider, result["ok"], result["message"])

    return APIResponse(
        code=0,
        data=result,
        message="连接成功" if result["ok"] else result["message"],
    )
