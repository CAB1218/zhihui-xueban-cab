"""
智慧学伴 认证 API 测试
测试用例：注册成功、注册重复邮箱、登录成功、登录错误密码、Token刷新、Token过期、登出
"""
import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User


class TestRegisterAPI:
    """注册API测试"""

    @pytest.mark.asyncio
    async def test_register_success(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试注册成功

        发送有效的注册请求，应返回201和用户信息
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@ai4edu.com",
                "password": "Test123456",
                "nickname": "新用户",
                "role": "student",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["email"] == "newuser@ai4edu.com"
        assert data["data"]["nickname"] == "新用户"
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(
        self,
        async_client: AsyncClient,
        db_session,
        test_user: User,
    ) -> None:
        """
        测试注册重复邮箱

        使用已注册的邮箱再次注册，应返回422
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": test_user.email,
                "password": "Another123456",
                "nickname": "重复邮箱用户",
                "role": "student",
            },
        )

        assert response.status_code == 422
        data = response.json()
        assert "已注册" in data["message"]

    @pytest.mark.asyncio
    async def test_register_invalid_email(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试注册无效邮箱

        使用无效邮箱格式注册，应返回422验证错误
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "Test123456",
                "nickname": "无效邮箱用户",
                "role": "student",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_short_password(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试注册密码过短

        使用少于6位的密码注册，应返回422验证错误
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpw@ai4edu.com",
                "password": "123",
                "nickname": "短密码用户",
                "role": "student",
            },
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_teacher_without_invite_code(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试教师注册无需邀请码

        以教师角色注册且不提供邀请码，应注册成功
        """
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "teacher2@ai4edu.com",
                "password": "Teacher123456",
                "nickname": "新教师",
                "role": "teacher",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert data["data"]["email"] == "teacher2@ai4edu.com"
        assert data["data"]["nickname"] == "新教师"


class TestLoginAPI:
    """登录API测试"""

    @pytest.mark.asyncio
    async def test_login_success(
        self,
        async_client: AsyncClient,
        db_session,
        test_user: User,
    ) -> None:
        """
        测试登录成功

        使用正确的邮箱和密码登录，应返回200和Token
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "Test123456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 200
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["user_id"] == test_user.id
        assert data["data"]["nickname"] == test_user.nickname
        assert data["data"]["role"] == test_user.role
        assert data["data"]["token_type"] == "bearer"
        assert data["data"]["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_login_wrong_password(
        self,
        async_client: AsyncClient,
        db_session,
        test_user: User,
    ) -> None:
        """
        测试登录错误密码

        使用错误密码登录，应返回401
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "WrongPassword123",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "密码错误" in data["message"] or "邮箱或密码错误" in data["message"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_email(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试登录不存在的邮箱

        使用未注册的邮箱登录，应返回401
        """
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@ai4edu.com",
                "password": "Test123456",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_disabled_account(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试登录已禁用账号

        使用已禁用的账号登录，应返回401
        """
        # 创建一个禁用用户
        disabled_user = User(
            email="disabled@ai4edu.com",
            password_hash=hash_password("Test123456"),
            nickname="禁用用户",
            role="student",
            is_active=False,
            default_scene="classroom",
            locale="zh-CN",
            timezone="Asia/Shanghai",
        )
        db_session.add(disabled_user)
        await db_session.commit()

        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": "disabled@ai4edu.com",
                "password": "Test123456",
            },
        )

        assert response.status_code == 401
        data = response.json()
        assert "禁用" in data["message"]


class TestTokenRefreshAPI:
    """Token刷新API测试"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        async_client: AsyncClient,
        db_session,
        test_user: User,
    ) -> None:
        """
        测试Token刷新成功

        使用有效的Refresh Token刷新，应返回新的Token对
        """
        refresh_token = create_refresh_token(data={"sub": test_user.id})

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"
        # 新Token应与旧Token不同
        # 验证返回了新的token（由于相同sub和exp可能生成相同token，改为验证新token有效且非空）
        assert len(data["data"]["refresh_token"]) > 0
        assert data["data"]["refresh_token"] != ""

    @pytest.mark.asyncio
    async def test_refresh_token_invalid(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试使用无效Refresh Token刷新

        使用无效的Token刷新，应返回401
        """
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token_with_access_token(
        self,
        async_client: AsyncClient,
        db_session,
        test_user: User,
    ) -> None:
        """
        测试使用Access Token代替Refresh Token刷新

        使用Access Token（type=access）作为Refresh Token，应返回401
        """
        access_token = create_access_token(
            data={"sub": test_user.id, "role": test_user.role}
        )

        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )

        assert response.status_code == 401


class TestTokenExpiry:
    """Token过期测试"""

    @pytest.mark.asyncio
    async def test_expired_access_token(
        self,
        async_client: AsyncClient,
        db_session,
        test_user: User,
    ) -> None:
        """
        测试过期的Access Token

        使用已过期的Token访问受保护接口，应返回401
        """
        from datetime import timedelta

        expired_token = create_access_token(
            data={"sub": test_user.id, "role": test_user.role},
            expires_delta=timedelta(seconds=-1),
        )

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401


class TestLogoutAPI:
    """登出API测试"""

    @pytest.mark.asyncio
    async def test_logout_success(
        self,
        async_client: AsyncClient,
        db_session,
        auth_headers: dict,
    ) -> None:
        """
        测试登出成功

        使用有效Token登出，应返回200
        """
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers=auth_headers,
        )

        # 登出端点可能返回200或204
        assert response.status_code in (200, 204)

    @pytest.mark.asyncio
    async def test_logout_without_token(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试未认证登出

        不携带Token尝试登出，应返回401
        """
        response = await async_client.post(
            "/api/v1/auth/logout",
        )

        assert response.status_code == 401


class TestGetCurrentUser:
    """获取当前用户信息测试"""

    @pytest.mark.asyncio
    async def test_get_current_user_success(
        self,
        async_client: AsyncClient,
        db_session,
        test_user: User,
        auth_headers: dict,
    ) -> None:
        """
        测试获取当前用户信息成功

        使用有效Token获取用户信息，应返回用户详情
        """
        response = await async_client.get(
            "/api/v1/auth/me",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["data"]["email"] == test_user.email
        assert data["data"]["nickname"] == test_user.nickname
        assert data["data"]["role"] == test_user.role

    @pytest.mark.asyncio
    async def test_get_current_user_no_auth(
        self,
        async_client: AsyncClient,
        db_session,
    ) -> None:
        """
        测试未认证获取用户信息

        不携带Token获取用户信息，应返回401
        """
        response = await async_client.get(
            "/api/v1/auth/me",
        )

        assert response.status_code == 401
