"""API Gateway app factory — docs/architecture/02-system-architecture.md §2.2.

"Single entry point for all client traffic. Owns authentication ..,
authorization pre-checks, rate limiting, request correlation-ID assignment
.., and request/response schema validation. No business logic lives here —
it is a thin, replaceable edge."

Milestone 0 scope only: health, correlation-ID middleware, OTel wiring, and
the synthetic-trace diagnostic endpoint that proves the Gateway -> Workflow
Engine -> Postgres checkpoint path works. Real business routers (workflow
submission, approval actions, etc.) are added from Milestone 1 onward as the
agents/services behind them exist — this file is the extension point, not
where that logic lives.
"""

from __future__ import annotations

from fastapi import FastAPI

from services.api_gateway.middleware import CorrelationIdMiddleware
from services.api_gateway.routers import diagnostics, health
from services.api_gateway.telemetry import instrument_app
from shared.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title='MARA AI-ETC API Gateway',
        description='Single entry point for all officer-workspace traffic. '
        'See docs/architecture/02-system-architecture.md §2.2.',
        version='0.1.0-milestone0',
    )

    app.add_middleware(CorrelationIdMiddleware)
    instrument_app(app, settings)

    app.include_router(health.router)
    app.include_router(diagnostics.router)

    return app
