"""
智慧学伴 端到端集成测试
验证完整的用户工作流：注册→登录→资源浏览→笔记→搜索
"""
import pytest
from httpx import AsyncClient


class TestAuthWorkflow:
    """认证工作流集成测试"""

    @pytest.mark.asyncio
    async def test_register_login_me_workflow(self, async_client: AsyncClient):
        """完整注册→登录→获取用户信息工作流"""
        # Step 1: 注册新用户
        register_data = {
            "email": "integration@test.com",
            "password": "Test@2024Secure",
            "nickname": "集成测试用户",
            "role": "student",
        }
        response = await async_client.post("/api/v1/auth/register", json=register_data)
        assert response.status_code in (200, 201), f"Register failed: {response.text}"

        # Step 2: 登录获取 Token
        login_data = {
            "email": "integration@test.com",
            "password": "Test@2024Secure",
        }
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200, f"Login failed: {response.text}"
        token_data = response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data

        access_token = token_data["access_token"]

        # Step 3: 使用 Token 获取用户信息
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200, f"Get me failed: {response.text}"
        user_data = response.json()
        assert user_data["email"] == "integration@test.com"

    @pytest.mark.asyncio
    async def test_refresh_token_workflow(self, async_client: AsyncClient):
        """Token 刷新工作流"""
        # 注册并登录
        register_data = {
            "email": "refresh@test.com",
            "password": "Test@2024Secure",
            "nickname": "刷新测试用户",
            "role": "student",
        }
        await async_client.post("/api/v1/auth/register", json=register_data)

        login_data = {"email": "refresh@test.com", "password": "Test@2024Secure"}
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        token_data = response.json()
        refresh_token = token_data["refresh_token"]

        # 使用 refresh_token 获取新 token
        response = await async_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200, f"Refresh failed: {response.text}"
        new_token_data = response.json()
        assert "access_token" in new_token_data


class TestResourceNoteWorkflow:
    """资源与笔记工作流集成测试"""

    @pytest.mark.asyncio
    async def test_create_and_list_notes(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """创建笔记→列表查询工作流"""
        # 创建笔记
        note_data = {
            "title": "集成测试笔记",
            "content": "这是通过集成测试创建的笔记",
            "note_type": "personal",
            "tags": ["测试", "集成"],
        }
        response = await async_client.post(
            "/api/v1/notes/",
            json=note_data,
            headers=auth_headers,
            follow_redirects=True,
        )
        assert response.status_code in (200, 201, 307), f"Create note failed: {response.text}"

        # 查询笔记列表
        response = await async_client.get(
            "/api/v1/notes/",
            headers=auth_headers,
            follow_redirects=True,
        )
        assert response.status_code == 200, f"List notes failed: {response.text}"


class TestHealthCheck:
    """健康检查集成测试"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client: AsyncClient):
        """健康检查端点"""
        response = await async_client.get("/health")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_api_docs_accessible(self, async_client: AsyncClient):
        """API 文档可访问"""
        response = await async_client.get("/docs")
        assert response.status_code == 200


class TestTelemetryEndpoint:
    """遥测端点集成测试"""

    @pytest.mark.asyncio
    async def test_telemetry_batch_report(self, async_client: AsyncClient):
        """批量遥测数据上报"""
        telemetry_data = {
            "sessionId": "test-session-001",
            "userAgent": "test-agent",
            "url": "http://localhost:5173/test",
            "events": [
                {
                    "type": "page_view",
                    "payload": {"path": "/test", "title": "Test Page"},
                },
                {
                    "type": "web_vital",
                    "payload": {"name": "LCP", "value": 1200, "rating": "good"},
                },
                {
                    "type": "error",
                    "payload": {
                        "type": "js_error",
                        "message": "Test error",
                    },
                },
            ],
        }
        response = await async_client.post(
            "/api/v1/telemetry",
            json=telemetry_data,
        )
        assert response.status_code == 200, f"Telemetry report failed: {response.text}"
        result = response.json()
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_telemetry_empty_events(self, async_client: AsyncClient):
        """空事件上报"""
        response = await async_client.post(
            "/api/v1/telemetry",
            json={"events": [], "sessionId": "test"},
        )
        assert response.status_code == 200
        result = response.json()
        assert result["processed"] == 0
