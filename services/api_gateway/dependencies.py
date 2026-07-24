"""Shared FastAPI dependency providers for business routers.

Deliberately typed against ``ResumableWorkflow`` (a structural protocol,
``services/approval_service/approval_service.py``) rather than a concrete
``agents``/``workflows`` type — per docs/architecture/03-repository-structure.md
§3.3, ``services/`` must not import from ``agents/`` or ``workflows/``. The
*concrete* compiled workflow graph is constructed once in
``services/api_gateway/composition.py`` (see that module's docstring for why
that one file is a deliberate, narrow exception to the same rule) and handed
to the app via ``app.state`` — routers, and this module, never import
``agents/`` or ``workflows/`` directly.
"""

from __future__ import annotations

from fastapi import Request

from services.approval_service.approval_service import (
    AsyncAuditWriter,
    ResumableWorkflow,
)


def get_workflow(request: Request) -> ResumableWorkflow:
    """The compiled Document Assessment workflow graph, set on
    ``app.state.workflow`` at startup (see ``composition.py`` for
    production, ``create_app(workflow=...)`` for tests)."""

    return request.app.state.workflow


def get_audit_writer(request: Request) -> AsyncAuditWriter | None:
    """The real Audit Memory writer, if wired (see ``composition.py``'s
    ``build_real_audit_writer``). ``None`` falls back to
    ``services/approval_service``'s structured-logging stub — routers don't
    need to know which case they're in."""

    return getattr(request.app.state, 'audit_writer', None)
