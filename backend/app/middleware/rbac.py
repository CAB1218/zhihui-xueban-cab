"""
智慧学伴 RBAC 权限中间件
基于角色的访问控制，支持装饰器 + 权限缓存 + 细粒度权限校验
"""
import functools
import time
from typing import Callable, Dict, List, Optional, Set

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger()


# ============ 权限缓存 ============

class PermissionCache:
    """
    权限缓存（进程内 TTL 缓存）

    减少每次请求查库的开销，默认 TTL 300 秒
    """

    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, tuple[list[str], float]] = {}
        self._ttl = ttl

    def get(self, key: str) -> Optional[List[str]]:
        """获取缓存权限列表"""
        entry = self._cache.get(key)
        if entry is None:
            return None
        permissions, timestamp = entry
        if time.time() - timestamp > self._ttl:
            del self._cache[key]
            return None
        return permissions

    def set(self, key: str, permissions: List[str]) -> None:
        """设置缓存"""
        self._cache[key] = (permissions, time.time())

    def invalidate(self, key: Optional[str] = None) -> None:
        """失效缓存，key=None 清空全部"""
        if key is None:
            self._cache.clear()
        else:
            self._cache.pop(key, None)

    @property
    def size(self) -> int:
        return len(self._cache)


# 全局权限缓存实例
permission_cache = PermissionCache(ttl=300)


# ============ 路径权限映射 ============

# 路径与所需角色的映射规则
# 格式: {路径前缀: {HTTP方法: 允许的角色列表}}
ROLE_PERMISSIONS: Dict[str, Dict[str, Set[str]]] = {
    "/api/v1/teachers": {
        "GET": {"teacher", "admin", "super_admin"},
        "POST": {"teacher", "admin", "super_admin"},
        "PUT": {"teacher", "admin", "super_admin"},
        "DELETE": {"admin", "super_admin"},
    },
    "/api/v1/admin": {
        "GET": {"admin", "super_admin"},
        "POST": {"admin", "super_admin"},
        "PUT": {"admin", "super_admin"},
        "DELETE": {"super_admin"},
    },
    "/api/v1/classrooms": {
        "GET": {"student", "teacher", "admin", "super_admin"},
        "POST": {"teacher", "admin", "super_admin"},
        "PUT": {"teacher", "admin", "super_admin"},
        "DELETE": {"admin", "super_admin"},
    },
    "/api/v1/permissions": {
        "GET": {"admin", "super_admin"},
        "POST": {"super_admin"},
        "PUT": {"super_admin"},
        "DELETE": {"super_admin"},
    },
    "/api/v1/scenes": {
        "GET": {"student", "teacher", "admin", "super_admin"},
        "POST": {"student", "teacher", "admin", "super_admin"},
    },
    "/api/v1/users": {
        "GET": {"admin", "super_admin"},
        "POST": {"admin", "super_admin"},
        "PUT": {"student", "teacher", "admin", "super_admin"},
        "DELETE": {"super_admin"},
    },
}

# 细粒度权限映射: {权限标识: {HTTP方法: 允许的角色}}
FINE_GRAINED_PERMISSIONS: Dict[str, Dict[str, Set[str]]] = {
    "user:export": {"GET": {"admin", "super_admin"}},
    "user:delete": {"DELETE": {"super_admin"}},
    "role:manage": {"GET": {"super_admin"}, "POST": {"super_admin"}, "PUT": {"super_admin"}},
    "scene:configure": {"PUT": {"teacher", "admin", "super_admin"}},
    "resource:upload": {"POST": {"teacher", "admin", "super_admin"}},
    "resource:audit": {"PUT": {"admin", "super_admin"}},
    "knowledge:edit": {"PUT": {"teacher", "admin", "super_admin"}},
    "knowledge:delete": {"DELETE": {"admin", "super_admin"}},
    "ai:config": {"PUT": {"admin", "super_admin"}},
}


# ============ RBAC 中间件 ============

class RBACMiddleware(BaseHTTPMiddleware):
    """
    RBAC 权限中间件

    工作流程：
    1. 根据请求路径和HTTP方法，查找所需角色
    2. 从缓存或数据库获取用户权限
    3. 对比当前用户角色是否满足要求
    4. 权限不足返回 403

    注意：此中间件应在 AuthMiddleware 之后执行
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """中间件处理逻辑"""

        path = request.url.path
        method = request.method.upper()

        # 跳过非 API 路径
        if not path.startswith("/api/"):
            return await call_next(request)

        # 查找匹配的权限规则
        required_roles: Set[str] = set()
        for path_prefix, method_perms in ROLE_PERMISSIONS.items():
            if path.startswith(path_prefix):
                required_roles = method_perms.get(method, set())
                break

        # 无特定权限要求的路径直接放行
        if not required_roles:
            return await call_next(request)

        # 获取当前用户角色
        user_role = getattr(request.state, "user_role", None)
        user_id = getattr(request.state, "user_id", None)

        if user_role is None:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "data": None, "message": "未认证"},
            )

        # 尝试从缓存获取用户权限
        # Super administrators bypass all path-based role restrictions.
        if user_role == "super_admin":
            return await call_next(request)

        if user_id:
            cache_key = f"user_perms:{user_id}"
            cached_perms = permission_cache.get(cache_key)
            if cached_perms and user_role in required_roles:
                return await call_next(request)

        # 校验角色权限
        if user_role not in required_roles:
            logger.warning(
                "rbac_access_denied",
                path=path,
                method=method,
                user_role=user_role,
                required_roles=list(required_roles),
            )
            return JSONResponse(
                status_code=403,
                content={"code": 403, "data": None, "message": "权限不足"},
            )

        # 缓存权限
        if user_id:
            cache_key = f"user_perms:{user_id}"
            permission_cache.set(cache_key, [user_role])

        return await call_next(request)


# ============ 权限装饰器 ============

def require_permissions(*permissions: str):
    """
    权限检查装饰器（用于路由函数）

    用法:
        @router.get("/admin/users")
        @require_permissions("user:list", "user:export")
        async def list_admin_users(...):
            ...

    Args:
        permissions: 所需权限标识列表
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 从 kwargs 获取当前用户
            request: Optional[Request] = kwargs.get("request")
            current_user = kwargs.get("current_user")

            # 尝试从 args 获取
            if current_user is None:
                for arg in args:
                    if hasattr(arg, "role"):
                        current_user = arg
                        break

            if current_user is None:
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "data": None, "message": "未认证"},
                )

            # 检查权限
            user_permissions = getattr(current_user, "permissions", [])
            if isinstance(user_permissions, str):
                import json
                try:
                    user_permissions = json.loads(user_permissions)
                except (json.JSONDecodeError, TypeError):
                    user_permissions = []

            user_perms_set = set(user_permissions)
            required_perms_set = set(permissions)

            # 超级管理员自动拥有所有权限
            if getattr(current_user, "role", None) == "super_admin":
                return await func(*args, **kwargs)

            # 检查是否拥有所有必需权限
            if not required_perms_set.issubset(user_perms_set):
                missing = required_perms_set - user_perms_set
                logger.warning(
                    "permission_denied",
                    user_id=getattr(current_user, "id", None),
                    missing_permissions=list(missing),
                )
                return JSONResponse(
                    status_code=403,
                    content={"code": 403, "data": None, "message": f"缺少权限: {', '.join(missing)}"},
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


def require_any_permission(*permissions: str):
    """
    权限检查装饰器（满足任一权限即可）

    Args:
        permissions: 所需权限标识列表（满足其一即可）
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            if current_user is None:
                for arg in args:
                    if hasattr(arg, "role"):
                        current_user = arg
                        break

            if current_user is None:
                return JSONResponse(
                    status_code=401,
                    content={"code": 401, "data": None, "message": "未认证"},
                )

            if getattr(current_user, "role", None) == "super_admin":
                return await func(*args, **kwargs)

            user_permissions = set(getattr(current_user, "permissions", []))
            required = set(permissions)

            if not user_permissions.intersection(required):
                logger.warning(
                    "permission_denied",
                    user_id=getattr(current_user, "id", None),
                    required_permissions=list(required),
                )
                return JSONResponse(
                    status_code=403,
                    content={"code": 403, "data": None, "message": "权限不足"},
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator
