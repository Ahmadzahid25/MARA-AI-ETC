"""OpenTelemetry wiring for the Gateway — docs/architecture/12-observability.md §12.3.

"OpenTelemetry spans across the full request path: Gateway -> Planner/
Supervisor -> Workflow Engine node -> Agent Runtime -> Tool Runtime ->
external service, with the LangGraph run ID as the trace root."

This module sets up the Gateway's end of that chain: an OTLP exporter
pointed at the local collector (infrastructure/compose/docker-compose.
observability.yml) and FastAPI auto-instrumentation. Downstream services
(Milestone 1+) get the equivalent wiring in shared/telemetry/ when they're
built — duplicated intentionally at the Gateway for Milestone 0 rather than
waiting on a shared/telemetry/ module that has no other consumer yet.
"""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from shared.config import Settings


def configure_tracing(settings: Settings) -> trace.Tracer:
    resource = Resource.create({SERVICE_NAME: 'mara-api-gateway'})
    provider = TracerProvider(resource=resource)

    if settings.observability.otel_exporter_endpoint:
        exporter = OTLPSpanExporter(
            endpoint=settings.observability.otel_exporter_endpoint, insecure=True
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)
    return trace.get_tracer('mara.api_gateway')


def instrument_app(app: FastAPI, settings: Settings) -> None:
    configure_tracing(settings)
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        # opentelemetry-instrumentation-fastapi is an optional extra; the
        # Gateway still runs and still emits manually-created spans (see
        # routers/diagnostics.py) without it.
        pass
