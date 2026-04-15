"""OpenTelemetry instrumentation for ConsentChain API."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, DEPLOYMENT_ENVIRONMENT


def setup_telemetry(
    service_name: str = "consentchain-api",
    environment: str = "development",
    otlp_endpoint: str = "http://localhost:4317",
) -> TracerProvider:
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            DEPLOYMENT_ENVIRONMENT: environment,
        }
    )

    provider = TracerProvider(resource=resource)

    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    trace.set_tracer_provider(provider)

    return provider


def instrument_app(app) -> None:
    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument(enable_commenter=True, enable_statement_replayer=True)


from opentelemetry import trace

tracer = trace.get_tracer(__name__)


def trace_consent_operation(operation: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(f"consent.{operation}") as span:
                span.set_attribute("operation", operation)
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    raise

        return wrapper

    return decorator


def trace_blockchain_operation(operation: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            with tracer.start_as_current_span(f"blockchain.{operation}") as span:
                span.set_attribute("operation", operation)
                span.set_attribute("system", "algorand")
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    if hasattr(result, "tx_id"):
                        span.set_attribute("tx_id", result.tx_id)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.record_exception(e)
                    raise

        return wrapper

    return decorator


from dataclasses import dataclass
from typing import Optional
from datetime import datetime
import time


@dataclass
class ConsentMetrics:
    total_granted: int = 0
    total_revoked: int = 0
    total_expired: int = 0
    avg_grant_latency_ms: float = 0.0
    avg_revoke_latency_ms: float = 0.0
    blockchain_tx_count: int = 0
    webhook_deliveries: int = 0
    webhook_failures: int = 0


class MetricsCollector:
    def __init__(self):
        self._metrics = ConsentMetrics()
        self._grant_latencies: list[float] = []
        self._revoke_latencies: list[float] = []

    def record_grant(self, latency_ms: float):
        self._metrics.total_granted += 1
        self._grant_latencies.append(latency_ms)
        self._update_avg_grant_latency()

    def record_revoke(self, latency_ms: float):
        self._metrics.total_revoked += 1
        self._revoke_latencies.append(latency_ms)
        self._update_avg_revoke_latency()

    def record_expiry(self):
        self._metrics.total_expired += 1

    def record_blockchain_tx(self):
        self._metrics.blockchain_tx_count += 1

    def record_webhook_delivery(self, success: bool):
        self._metrics.webhook_deliveries += 1
        if not success:
            self._metrics.webhook_failures += 1

    def _update_avg_grant_latency(self):
        if self._grant_latencies:
            self._metrics.avg_grant_latency_ms = sum(self._grant_latencies) / len(
                self._grant_latencies
            )

    def _update_avg_revoke_latency(self):
        if self._revoke_latencies:
            self._metrics.avg_revoke_latency_ms = sum(self._revoke_latencies) / len(
                self._revoke_latencies
            )

    def get_metrics(self) -> ConsentMetrics:
        return self._metrics

    def reset(self):
        self._metrics = ConsentMetrics()
        self._grant_latencies = []
        self._revoke_latencies = []


metrics_collector = MetricsCollector()
