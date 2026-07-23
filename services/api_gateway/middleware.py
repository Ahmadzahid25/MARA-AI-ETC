"""Correlation-ID middleware — docs/architecture/02-system-architecture.md §2.2.

"Request correlation-ID assignment (used end-to-end for tracing, see
docs/architecture/12-observability.md)". The Gateway is the single place a
correlation ID is *assigned*; everything downstream (Supervisor, Agent
Runtime, Tool Runtime, Audit Memory writes) propagates it, never mints a new
one — that propagation is what lets an incident investigation pivot between
Loki/Prometheus/Langfuse/Audit Memory using one ID (docs/architecture/
12-observability.md §12.10).
"""

from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from shared.config import get_settings


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        header_name = get_settings().gateway_correlation_header
        correlation_id = request.headers.get(header_name) or str(uuid.uuid4())

        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[header_name] = correlation_id
        return response
