"""Diagnostics — Milestone 0's synthetic end-to-end trace endpoint.

docs/architecture/14-roadmap.md §14.2 acceptance criterion: "a synthetic
end-to-end trace (Gateway -> dummy workflow -> Postgres checkpoint) is
visible in Grafana/Langfuse." This router is that check, made callable.

Auditor-role-gated (not open to every officer) since it touches the
Workflow Engine and Postgres directly and is meant for platform
verification, not day-to-day officer use.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from opentelemetry import trace

from services.api_gateway.auth import Principal, require_role
from shared.config import Settings, get_settings
from shared.workflow_engine import run_synthetic_trace

router = APIRouter(prefix='/diagnostics', tags=['diagnostics'])
_tracer = trace.get_tracer('mara.api_gateway.diagnostics')

# Module-level singleton rather than a call inline in the signature default
# (ruff B008) — same dependency, just not re-constructed on every import.
_require_auditor = require_role('auditor')


@router.post('/synthetic-trace')
async def synthetic_trace(
    request: Request,
    settings: Settings = Depends(get_settings),
    principal: Principal = Depends(_require_auditor),
) -> dict[str, object]:
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')

    with _tracer.start_as_current_span('synthetic_trace') as span:
        span.set_attribute('mara.correlation_id', correlation_id)
        span.set_attribute('mara.triggered_by', principal.subject)

        result = await run_synthetic_trace(settings, correlation_id)

        span.set_attribute('mara.stage_log', ','.join(result['stage_log']))

    return {
        'correlation_id': correlation_id,
        'stage_log': result['stage_log'],
        'checkpointed': True,
    }
