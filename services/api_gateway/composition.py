"""Composition root — the one deliberate, narrow exception to
docs/architecture/03-repository-structure.md §3.3's rule that ``services/``
must not import from ``agents/`` or ``workflows/``.

That rule exists so services stay lower-level than orchestration and don't
reach up into agent/workflow internals piecemeal. It does not have an
obvious answer for *where the concrete wiring happens at all* — something,
somewhere, has to construct a real ``DocumentAgent``, a real
``ComplianceAgent``, and compile them into the real
``workflows.document_assessment`` graph before the Gateway can serve a
single request. Every other file in ``services/api_gateway`` (routers,
``dependencies.py``, ``app.py``) is kept clean of that import by depending
only on ``ResumableWorkflow`` (a structural protocol) — this module is
where the one unavoidable concrete construction happens, isolated on
purpose so it's the only place a reviewer needs to look to audit the
exception.

**Flagged for architecture review.** If the intended integration point is
actually meant to be ``services/supervisor_service`` (docs/architecture/
05-agent-architecture.md §5.10 — "dispatch tasks to agents... within the
active workflow template's declared graph" reads like exactly this job) once
that service exists, this module's construction logic should move there and
the Gateway should depend on supervisor_service's interface instead. Until
that service exists, this is the pragmatic choice: no other extant `services/`
module owns triggering a workflow run in-process today.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from agents.compliance_agent import ComplianceAgent
from agents.document_agent import DocumentAgent
from services.approval_service.approval_service import ResumableWorkflow
from shared.config import Settings
from shared.workflow_engine import postgres_checkpointer
from workflows.document_assessment import build_document_assessment_graph


@asynccontextmanager
async def build_real_workflow(settings: Settings) -> AsyncIterator[ResumableWorkflow]:
    """Construct the real Document Assessment workflow, checkpointed
    against the primary Postgres instance. No real OCR engine or document
    classifier is wired underneath ``DocumentAgent``/tools yet (see
    ``tools/ocr/README.md``, ``tools/documents/README.md``) — every request
    through this workflow will fail with a typed ``ToolExternalServiceError``
    at the classification/OCR step until one is. This is expected, current
    platform state, not a bug in this wiring.
    """

    document_agent = DocumentAgent()
    compliance_agent = ComplianceAgent()
    graph = build_document_assessment_graph(document_agent, compliance_agent)

    async with postgres_checkpointer(settings) as checkpointer:
        yield graph.compile(checkpointer=checkpointer)
