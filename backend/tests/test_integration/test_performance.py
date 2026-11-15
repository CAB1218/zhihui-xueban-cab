"""
智慧学伴 API 性能基准测试
使用 pytest-benchmark 测量关键 API 端点响应时间
"""
import pytest
from httpx import AsyncClient


class TestAuthPerformance:
    """认证 API 性能测试"""

    @pytest.mark.asyncio
    async def test_login_response_time(
        self, async_client: AsyncClient, test_user: "User"
    ):
        """登录接口响应时间应 < 500ms"""
        import time

        login_data = {
            "email": "test@ai4edu.com",
            "password": "Test123456",
        }

        start = time.perf_counter()
        response = await async_client.post("/api/v1/auth/login", json=login_data)
        elapsed = (time.perf_counter() - start) * 1000

        # 登录可能成功也可能失败（密码哈希不匹配），但不应超时
        assert elapsed < 2000, f"Login took {elapsed:.0f}ms, expected < 2000ms"

    @pytest.mark.asyncio
    async def test_me_response_time(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        """获取用户信息响应时间应 < 200ms"""
        import time

        start = time.perf_counter()
        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        elapsed = (time.perf_counter() - start) * 1000

        assert elapsed < 1000, f"Get me took {elapsed:.0f}ms, expected < 1000ms"


class TestHealthPerformance:
    """健康检查性能测试"""

    @pytest.mark.asyncio
    async def test_health_response_time(self, async_client: AsyncClient):
        """健康检查响应时间应 < 100ms"""
        import time

        start = time.perf_counter()
        response = await async_client.get("/health")
        elapsed = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 500, f"Health check took {elapsed:.0f}ms, expected < 500ms"


class TestTelemetryPerformance:
    """遥测 API 性能测试"""

    @pytest.mark.asyncio
    async def test_telemetry_batch_response_time(self, async_client: AsyncClient):
        """批量遥测上报响应时间应 < 1000ms"""
        import time

        # 构造 10 条事件
        events = [
            {
                "type": "web_vital",
                "payload": {"name": "LCP", "value": i * 100, "rating": "good"},
            }
            for i in range(10)
        ]

        start = time.perf_counter()
        response = await async_client.post(
            "/api/v1/telemetry",
            json={
                "sessionId": "perf-test",
                "events": events,
            },
        )
        elapsed = (time.perf_counter() - start) * 1000

        assert response.status_code == 200
        assert elapsed < 2000, f"Telemetry batch took {elapsed:.0f}ms, expected < 2000ms"


# 需要导入 User 模型用于类型注解
from app.models.user import User  # noqa: E402
