"""
智慧学伴 OpenTelemetry 可观测性配置
集成 Jaeger/Zipkin 链路追踪 + Prometheus 指标
"""
import logging
import time
from typing import Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


# ============ Prometheus 指标定义 ============

class PrometheusMetrics:
    """
    Prometheus 自定义指标集合

    指标：
    - ai4edu_http_requests_total: HTTP请求计数（按method/path/status）
    - ai4edu_request_duration_seconds: 请求响应时间直方图
    - ai4edu_active_websocket_connections: 活跃WebSocket连接数
    - ai4edu_ai_calls_total: AI调用次数（按model/type/status）
    - ai4edu_ai_call_duration_seconds: AI调用延迟直方图
    """

    def __init__(self) -> None:
        """初始化Prometheus指标"""
        try:
            from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
            from prometheus_client import CollectorRegistry

            self._registry = REGISTRY

            # HTTP请求总数
            self.http_requests_total = Counter(
                "ai4edu_http_requests_total",
                "Total count of HTTP requests",
                ["method", "path", "status_code"],
                registry=self._registry,
            )

            # 请求响应时间
            self.request_duration_seconds = Histogram(
                "ai4edu_request_duration_seconds",
                "HTTP request duration in seconds",
                ["method", "path"],
                buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0],
                registry=self._registry,
            )

            # 活跃WebSocket连接数
            self.active_websocket_connections = Gauge(
                "ai4edu_active_websocket_connections",
                "Number of active WebSocket connections",
                registry=self._registry,
            )

            # AI调用总数
            self.ai_calls_total = Counter(
                "ai4edu_ai_calls_total",
                "Total count of AI service calls",
                ["model", "call_type", "status"],
                registry=self._registry,
            )

            # AI调用延迟
            self.ai_call_duration_seconds = Histogram(
                "ai4edu_ai_call_duration_seconds",
                "AI service call duration in seconds",
                ["model", "call_type"],
                buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0, 60.0],
                registry=self._registry,
            )

            self._available = True
        except ImportError:
            logger.warning("prometheus_client not installed, metrics collection disabled")
            self._available = False

    @property
    def available(self) -> bool:
        """检查Prometheus是否可用"""
        return self._available

    def record_http_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration: float,
    ) -> None:
        """
        记录HTTP请求指标

        Args:
            method: HTTP方法
            path: 请求路径
            status_code: 响应状态码
            duration: 请求耗时（秒）
        """
        if not self._available:
            return

        # 规范化路径，避免高基数标签
        normalized_path = self._normalize_path(path)

        self.http_requests_total.labels(
            method=method,
            path=normalized_path,
            status_code=str(status_code),
        ).inc()

        self.request_duration_seconds.labels(
            method=method,
            path=normalized_path,
        ).observe(duration)

    def record_ai_call(
        self,
        model: str,
        call_type: str,
        status: str,
        duration: float,
    ) -> None:
        """
        记录AI调用指标

        Args:
            model: 模型名称
            call_type: 调用类型 (chat/embedding/etc)
            status: 调用状态 (success/error/rate_limited)
            duration: 调用耗时（秒）
        """
        if not self._available:
            return

        self.ai_calls_total.labels(
            model=model,
            call_type=call_type,
            status=status,
        ).inc()

        self.ai_call_duration_seconds.labels(
            model=model,
            call_type=call_type,
        ).observe(duration)

    def increment_websocket_connections(self) -> None:
        """增加活跃WebSocket连接计数"""
        if self._available:
            self.active_websocket_connections.inc()

    def decrement_websocket_connections(self) -> None:
        """减少活跃WebSocket连接计数"""
        if self._available:
            self.active_websocket_connections.dec()

    def set_websocket_connections(self, count: float) -> None:
        """设置活跃WebSocket连接数"""
        if self._available:
            self.active_websocket_connections.set(count)

    def generate_metrics(self) -> str:
        """
        生成Prometheus格式的指标数据

        Returns:
            str: Prometheus文本格式指标数据
        """
        if not self._available:
            return ""

        from prometheus_client import generate_latest
        return generate_latest(self._registry).decode("utf-8")

    @staticmethod
    def _normalize_path(path: str) -> str:
        """
        规范化URL路径，将动态段替换为占位符

        避免高基数标签（如 /api/v1/users/123 → /api/v1/users/:id）

        Args:
            path: 原始路径

        Returns:
            str: 规范化后的路径
        """
        parts = path.strip("/").split("/")
        normalized_parts = []

        for i, part in enumerate(parts):
            # 数字ID替换为 :id
            if part.isdigit():
                normalized_parts.append(":id")
            # UUID替换为 :uuid
            elif len(part) == 36 and part.count("-") == 4:
                normalized_parts.append(":uuid")
            else:
                normalized_parts.append(part)

        return "/" + "/".join(normalized_parts)


# 全局指标实例
metrics = PrometheusMetrics()


# ============ Metrics HTTP 端点 ============

async def metrics_endpoint(request: Request) -> Response:
    """
    Prometheus指标抓取端点

    GET /metrics 返回Prometheus格式的指标数据

    Args:
        request: FastAPI请求对象

    Returns:
        PlainTextResponse: Prometheus文本格式指标
    """
    content = metrics.generate_metrics()
    return PlainTextResponse(
        content=content,
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


# ============ 指标采集中间件 ============

class MetricsMiddleware(BaseHTTPMiddleware):
    """
    HTTP请求指标采集中间件

    自动采集每个请求的方法、路径、状态码和响应时间
    排除 /metrics 端点自身，避免自引用
    """

    # 不采集指标的路径
    EXCLUDED_PATHS = {"/metrics", "/health", "/readiness"}

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        采集请求指标并传递到下一层

        Args:
            request: 请求对象
            call_next: 下一个中间件/处理器

        Returns:
            Response: 响应对象
        """
        # 跳过排除的路径
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration = time.perf_counter() - start_time

            metrics.record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration=duration,
            )

            return response
        except Exception as exc:
            duration = time.perf_counter() - start_time

            # 异常请求记录为500
            metrics.record_http_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration=duration,
            )
            raise


# ============ OpenTelemetry 链路追踪配置 ============

def setup_telemetry() -> None:
    """
    初始化 OpenTelemetry 配置

    配置内容：
    - tracer provider
    - FastAPI 自动 instrumentation
    - OTLP exporter 导出到 Jaeger/Zipkin
    - meter provider 用于 Prometheus 指标

    当前为占位实现，后续版本启用。
    """
    try:
        from opentelemetry import trace
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
            )
        )
        trace.set_tracer_provider(provider)

        logger.info(
            f"OpenTelemetry configured: service={settings.OTEL_SERVICE_NAME}, "
            f"endpoint={settings.OTEL_EXPORTER_OTLP_ENDPOINT}"
        )
    except ImportError:
        logger.warning(
            "OpenTelemetry packages not installed, tracing disabled. "
            "Install opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp-proto-grpc, "
            "opentelemetry-instrumentation-fastapi to enable tracing."
        )
    except Exception as e:
        logger.error(f"Failed to setup OpenTelemetry: {e}")


def instrument_app(app: FastAPI) -> None:
    """
    对FastAPI应用进行OpenTelemetry自动instrument

    Args:
        app: FastAPI应用实例
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("FastAPIInstrumentor not available, skipping instrumentation")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}")
