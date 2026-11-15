"""
智慧学伴 用户 Service
处理用户信息查询、更新、偏好设置、Onboarding 引导等业务逻辑
"""
import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.exceptions import NotFoundException, ValidationException
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate, OnboardingRequest


class UserService:
    """用户服务"""

    def __init__(self, db: AsyncSession):
        """初始化用户服务"""
        self.db = db

    async def get_user(self, user_id: int) -> UserResponse:
        """
        获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            UserResponse: 用户信息

        Raises:
            NotFoundException: 用户不存在
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise NotFoundException(message="用户不存在")

        return self._to_response(user)

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        role: Optional[str] = None,
        search: Optional[str] = None,
    ) -> dict:
        """
        获取用户列表

        Args:
            page: 页码
            page_size: 每页数量
            role: 角色筛选
            search: 搜索关键词

        Returns:
            dict: 分页用户列表
        """
        query = select(User).where(User.deleted_at.is_(None))

        # 角色筛选
        if role:
            query = query.where(User.role == role)

        # 搜索
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (User.nickname.ilike(search_term)) | (User.email.ilike(search_term))
            )

        # 计算总数
        from sqlalchemy import func
        count_query = select(func.count()).select_from(User).where(User.deleted_at.is_(None))
        if role:
            count_query = count_query.where(User.role == role)
        if search:
            search_term = f"%{search}%"
            count_query = count_query.where(
                (User.nickname.ilike(search_term)) | (User.email.ilike(search_term))
            )
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = query.order_by(User.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        users = result.scalars().all()

        return {
            "items": [self._to_response(u) for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    async def update_user(self, user_id: int, data: UserUpdate) -> UserResponse:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            data: 更新数据

        Returns:
            UserResponse: 更新后的用户信息

        Raises:
            NotFoundException: 用户不存在
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise NotFoundException(message="用户不存在")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)

        await self.db.commit()
        await self.db.refresh(user)

        return self._to_response(user)

    async def update_preferences(self, user_id: int, preferences: dict) -> UserResponse:
        """
        更新用户偏好设置

        Args:
            user_id: 用户ID
            preferences: 偏好数据

        Returns:
            UserResponse: 更新后的用户信息
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise NotFoundException(message="用户不存在")

        # 合并偏好
        current_prefs = {}
        if user.preferences:
            try:
                current_prefs = json.loads(user.preferences)
            except (json.JSONDecodeError, TypeError):
                current_prefs = {}

        current_prefs.update(preferences)
        user.preferences = json.dumps(current_prefs, ensure_ascii=False)

        # 处理特殊字段
        if "default_scene" in preferences:
            user.default_scene = preferences["default_scene"]
        if "locale" in preferences:
            user.locale = preferences["locale"]

        await self.db.commit()
        await self.db.refresh(user)

        return self._to_response(user)

    async def change_password(self, user_id: int, old_password: str, new_password: str) -> None:
        """
        修改密码

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Raises:
            NotFoundException: 用户不存在
            ValidationException: 旧密码不正确
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise NotFoundException(message="用户不存在")

        if not verify_password(old_password, user.password_hash):
            raise ValidationException(message="旧密码不正确")

        user.password_hash = hash_password(new_password)
        await self.db.commit()

    async def complete_onboarding(self, user_id: int, request: OnboardingRequest) -> dict:
        """
        完成用户引导

        根据引导信息更新用户角色、兴趣、目标，并推荐默认场景

        Args:
            user_id: 用户ID
            request: 引导请求

        Returns:
            dict: 引导完成结果
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise NotFoundException(message="用户不存在")

        # 更新用户信息
        user.role = request.role
        user.grade = request.grade
        user.school = request.school
        user.major = request.major
        user.onboarding_completed = True

        # 保存兴趣和目标到偏好
        preferences = {}
        if user.preferences:
            try:
                preferences = json.loads(user.preferences)
            except (json.JSONDecodeError, TypeError):
                preferences = {}

        preferences["interests"] = request.interests
        preferences["goals"] = request.goals
        preferences["onboarding_completed_at"] = datetime.utcnow().isoformat()

        user.preferences = json.dumps(preferences, ensure_ascii=False)

        # 根据角色和目标推荐默认场景
        default_scene = self._recommend_default_scene(request.role, request.goals)
        user.default_scene = default_scene

        await self.db.commit()
        await self.db.refresh(user)

        return {
            "user_id": user.id,
            "onboarding_completed": user.onboarding_completed,
            "default_scene": user.default_scene,
            "message": "引导完成",
        }

    async def delete_user(self, user_id: int) -> None:
        """
        软删除用户

        Args:
            user_id: 用户ID

        Raises:
            NotFoundException: 用户不存在
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise NotFoundException(message="用户不存在")

        user.deleted_at = datetime.utcnow()
        user.is_active = False
        await self.db.commit()

    def _recommend_default_scene(self, role: str, goals: list[str]) -> str:
        """
        根据角色和目标推荐默认场景

        Args:
            role: 用户角色
            goals: 学习目标列表

        Returns:
            str: 推荐场景类型
        """
        goal_scene_map = {
            "考试提分": "exam",
            "系统学习": "self_study",
            "课堂同步": "classroom",
            "协作交流": "discussion",
        }

        # 根据目标优先匹配
        for goal in goals:
            if goal in goal_scene_map:
                return goal_scene_map[goal]

        # 根据角色推荐
        role_scene_map = {
            "student": "classroom",
            "teacher": "classroom",
        }
        return role_scene_map.get(role, "classroom")

    def _to_response(self, user: User) -> UserResponse:
        """将 User ORM 对象转换为 UserResponse"""
        return UserResponse(
            id=user.id,
            email=user.email,
            nickname=user.nickname,
            avatar_url=user.avatar_url,
            role=user.role,
            phone=user.phone,
            grade=user.grade,
            school=user.school,
            major=user.major,
            bio=user.bio,
            default_scene=user.default_scene,
            locale=user.locale,
            onboarding_completed=user.onboarding_completed,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
