"""
智慧学伴 权限管理 API
提供角色 CRUD、权限分配、用户角色管理等 RBAC 完整端点
"""
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.permission import Role, Permission, RolePermission, UserRole
from app.schemas.common import APIResponse, PaginationParams
from app.dependencies import get_current_user, require_role
from app.models.user import User

router = APIRouter()


# ============ Schema ============

class RoleCreateRequest(BaseModel):
    """创建角色请求"""
    name: str = Field(..., min_length=2, max_length=50, description="角色标识")
    display_name: str = Field(..., min_length=2, max_length=100, description="显示名称")
    description: Optional[str] = Field(default=None, description="角色描述")


class RoleUpdateRequest(BaseModel):
    """更新角色请求"""
    display_name: Optional[str] = Field(default=None, max_length=100, description="显示名称")
    description: Optional[str] = Field(default=None, description="角色描述")


class PermissionAssignRequest(BaseModel):
    """分配权限请求"""
    permission_ids: List[int] = Field(..., min_length=1, description="权限ID列表")


class UserRoleAssignRequest(BaseModel):
    """分配角色请求"""
    role_ids: List[int] = Field(..., min_length=1, description="角色ID列表")


class RoleResponse(BaseModel):
    """角色响应"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system: bool
    permissions: List[dict] = Field(default_factory=list, description="角色拥有的权限列表")


class PermissionResponse(BaseModel):
    """权限响应"""
    id: int
    name: str
    display_name: str
    module: str
    description: Optional[str]


# ============ 角色管理 ============

@router.get("/roles", response_model=APIResponse[list], summary="获取角色列表")
async def list_roles(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "super_admin"])),
) -> APIResponse[list]:
    """获取所有角色定义（含每个角色的权限列表）"""
    result = await db.execute(select(Role).order_by(Role.id))
    roles = result.scalars().all()

    role_list = []
    for role in roles:
        # 查询角色权限
        perm_result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
        perms = perm_result.scalars().all()

        role_list.append({
            "id": role.id,
            "name": role.name,
            "display_name": role.display_name,
            "description": role.description,
            "is_system": role.is_system,
            "permissions": [
                {"id": p.id, "name": p.name, "display_name": p.display_name, "module": p.module}
                for p in perms
            ],
        })

    return APIResponse(data=role_list)


@router.post("/roles", response_model=APIResponse[dict], summary="创建角色")
async def create_role(
    request: RoleCreateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["super_admin"])),
) -> APIResponse[dict]:
    """创建新角色"""
    # 检查角色名唯一
    existing = await db.execute(select(Role).where(Role.name == request.name))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="角色标识已存在")

    role = Role(
        name=request.name,
        display_name=request.display_name,
        description=request.description,
        is_system=False,
    )
    db.add(role)
    await db.commit()
    await db.refresh(role)

    return APIResponse(data={
        "id": role.id,
        "name": role.name,
        "display_name": role.display_name,
    })


@router.put("/roles/{role_id}", response_model=APIResponse[dict], summary="更新角色")
async def update_role(
    role_id: int,
    request: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["super_admin"])),
) -> APIResponse[dict]:
    """更新角色信息"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    if request.display_name is not None:
        role.display_name = request.display_name
    if request.description is not None:
        role.description = request.description

    await db.commit()
    return APIResponse(data={
        "id": role.id,
        "name": role.name,
        "display_name": role.display_name,
    })


@router.delete("/roles/{role_id}", response_model=APIResponse[None], summary="删除角色")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["super_admin"])),
) -> APIResponse[None]:
    """删除自定义角色（系统内置角色不可删除）"""
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统内置角色不可删除")

    await db.delete(role)
    await db.commit()
    return APIResponse(message="角色已删除")


# ============ 权限管理 ============

@router.get("/permissions", response_model=APIResponse[list], summary="获取权限列表")
async def list_permissions(
    module: Optional[str] = Query(None, description="按模块筛选"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "super_admin"])),
) -> APIResponse[list]:
    """获取所有权限定义，支持按模块筛选"""
    query = select(Permission).order_by(Permission.module, Permission.id)
    if module:
        query = query.where(Permission.module == module)

    result = await db.execute(query)
    perms = result.scalars().all()

    return APIResponse(data=[
        {
            "id": p.id,
            "name": p.name,
            "display_name": p.display_name,
            "module": p.module,
            "description": p.description,
        }
        for p in perms
    ])


@router.post("/roles/{role_id}/permissions", response_model=APIResponse[dict], summary="分配权限给角色")
async def assign_permissions_to_role(
    role_id: int,
    request: PermissionAssignRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["super_admin"])),
) -> APIResponse[dict]:
    """为角色分配权限"""
    # 检查角色存在
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalars().first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")

    # 获取已有权限
    existing_result = await db.execute(
        select(RolePermission.permission_id).where(RolePermission.role_id == role_id)
    )
    existing_ids = {row[0] for row in existing_result.all()}

    # 添加新权限
    added = []
    for perm_id in request.permission_ids:
        if perm_id not in existing_ids:
            # 验证权限存在
            perm_result = await db.execute(select(Permission).where(Permission.id == perm_id))
            if perm_result.scalars().first():
                rp = RolePermission(role_id=role_id, permission_id=perm_id)
                db.add(rp)
                added.append(perm_id)

    await db.commit()

    # 清除权限缓存
    from app.middleware.rbac import permission_cache
    permission_cache.invalidate()

    return APIResponse(data={"role_id": role_id, "added_permission_ids": added})


@router.delete("/roles/{role_id}/permissions", response_model=APIResponse[dict], summary="移除角色权限")
async def remove_permissions_from_role(
    role_id: int,
    request: PermissionAssignRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["super_admin"])),
) -> APIResponse[dict]:
    """移除角色的指定权限"""
    for perm_id in request.permission_ids:
        result = await db.execute(
            select(RolePermission).where(
                RolePermission.role_id == role_id,
                RolePermission.permission_id == perm_id,
            )
        )
        rp = result.scalars().first()
        if rp:
            await db.delete(rp)

    await db.commit()

    from app.middleware.rbac import permission_cache
    permission_cache.invalidate()

    return APIResponse(data={"role_id": role_id, "removed_permission_ids": request.permission_ids})


# ============ 用户角色管理 ============

@router.post("/users/{user_id}/roles", response_model=APIResponse[dict], summary="分配角色给用户")
async def assign_role_to_user(
    user_id: int,
    request: UserRoleAssignRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "super_admin"])),
) -> APIResponse[dict]:
    """为用户分配角色"""
    # 检查用户存在
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 获取已有角色
    existing_result = await db.execute(
        select(UserRole.role_id).where(UserRole.user_id == user_id)
    )
    existing_ids = {row[0] for row in existing_result.all()}

    added = []
    for role_id in request.role_ids:
        if role_id not in existing_ids:
            role_result = await db.execute(select(Role).where(Role.id == role_id))
            if role_result.scalars().first():
                ur = UserRole(user_id=user_id, role_id=role_id)
                db.add(ur)
                added.append(role_id)

    await db.commit()

    from app.middleware.rbac import permission_cache
    permission_cache.invalidate(f"user_perms:{user_id}")

    return APIResponse(data={"user_id": user_id, "added_role_ids": added})


@router.get("/users/{user_id}/permissions", response_model=APIResponse[list], summary="获取用户权限")
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "super_admin"])),
) -> APIResponse[list]:
    """获取用户的所有权限（含角色继承）"""
    # 检查用户存在
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 超级管理员拥有所有权限
    if user.role == "super_admin":
        all_perms = await db.execute(select(Permission))
        return APIResponse(data=[
            {"id": p.id, "name": p.name, "display_name": p.display_name, "module": p.module}
            for p in all_perms.scalars().all()
        ])

    # 查询用户角色 -> 角色权限
    perm_result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(UserRole, UserRole.role_id == RolePermission.role_id)
        .where(UserRole.user_id == user_id)
        .distinct()
    )
    perms = perm_result.scalars().all()

    return APIResponse(data=[
        {"id": p.id, "name": p.name, "display_name": p.display_name, "module": p.module}
        for p in perms
    ])


@router.get("/modules", response_model=APIResponse[list], summary="获取权限模块列表")
async def list_permission_modules(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role(["admin", "super_admin"])),
) -> APIResponse[list]:
    """获取所有权限模块"""
    from sqlalchemy import func
    result = await db.execute(
        select(Permission.module, func.count(Permission.id))
        .group_by(Permission.module)
        .order_by(Permission.module)
    )
    modules = [{"name": row[0], "count": row[1]} for row in result.all()]
    return APIResponse(data=modules)
