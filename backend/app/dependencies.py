"""
AI4Edu 全局依赖注入
提供数据库会话、认证、权限等通用依赖
"""
from typing import AsyncGenerator, List

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

# HTTP Bearer 认证方案
security_scheme = HTTPBearer()


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> User:
    """
    从JWT Token中解析当前用户

    Args:
        request: 请求对象
        db: 数据库会话
        credentials: Bearer Token 凭据

    Returns:
        User: 当前认证用户

    Raises:
        HTTPException: 401 - Token无效或用户不存在
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token无效或已过期",
        )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token格式错误",
        )

    # 从数据库查询用户
    from sqlalchemy.future import select
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalars().first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号已禁用",
        )

    # 兼容历史自注册用户：tenant_id 为空时自动归属默认租户。
    # 否则各业务模块的 tenant_id=... or 0 会写入一个不存在的租户 id，
    # 触发 tenant_id 外键约束失败（前端表现为 500 服务器内部错误）。
    if user.tenant_id is None:
        from sqlalchemy import func

        from app.models.tenant import Tenant

        default_tenant_id = (await db.execute(select(func.min(Tenant.id)))).scalar()
        if default_tenant_id is not None:
            user.tenant_id = default_tenant_id
            await db.commit()
            await db.refresh(user)

    # 将用户信息附加到请求状态（供中间件使用）
    request.state.user_id = user.id
    request.state.user_role = user.role

    return user


def require_role(allowed_roles: List[str]):
    """
    角色权限检查装饰器

    Args:
        allowed_roles: 允许的角色列表，如 ["teacher", "admin"]

    Returns:
        依赖函数
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # 超级管理员拥有全部功能权限，不受具体角色白名单限制。
        if current_user.role == "super_admin":
            return current_user

        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="权限不足",
            )
        return current_user
    return role_checker


async def get_tenant_schema(
    current_user: User = Depends(get_current_user),
) -> str:
    """
    获取当前用户的租户Schema名称

    Args:
        current_user: 当前认证用户

    Returns:
        str: 租户Schema名称，如 tenant_1
    """
    if current_user.tenant_id is None:
        return "public"
    return f"tenant_{current_user.tenant_id}"


async def get_tenant_session(
    tenant_schema: str = Depends(get_tenant_schema),
) -> AsyncGenerator[AsyncSession, None]:
    """
    获取租户专属数据库会话

    Args:
        tenant_schema: 租户Schema名称

    Yields:
        AsyncSession: 租户隔离的数据库会话
    """
    from app.database import get_tenant_db
    async for session in get_tenant_db(tenant_schema):
        yield session
