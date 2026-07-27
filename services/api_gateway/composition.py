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
from agents.finance_agent import FinanceAgent
from agents.market_agent import MarketAgent
from agents.recommendation_agent import RecommendationAgent
from agents.risk_agent import RiskAgent
from services.approval_service.approval_service import (
    AsyncAuditWriter,
    ResumableWorkflow,
)
from services.audit_service import (
    approval_record_to_audit_event,
    audit_pool,
    write_audit_event,
)
from services.knowledge_service import DifyAdapter
from services.memory_service import calibration_pool, write_calibration_event
from shared.config import Settings
from shared.workflow_engine import postgres_checkpointer
from workflows.document_assessment import (
    CalibrationWriter,
    build_document_assessment_graph,
)
from workflows.loan_assessment import build_loan_assessment_graph


@asynccontextmanager
async def build_real_workflow(
    settings: Settings, calibration_writer: CalibrationWriter | None = None
) -> AsyncIterator[ResumableWorkflow]:
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
    graph = build_document_assessment_graph(
        document_agent, compliance_agent, calibration_writer=calibration_writer
    )

    async with postgres_checkpointer(settings) as checkpointer:
        yield graph.compile(checkpointer=checkpointer)


@asynccontextmanager
async def build_real_audit_writer(
    settings: Settings,
) -> AsyncIterator[AsyncAuditWriter]:
    """The real Audit Memory write path for approval decisions
    (services/audit_service, against the ``audit_memory`` table already
    defined in infrastructure/compose/init/postgres-primary-init.sql).
    Same composition-root reasoning as ``build_real_workflow`` above —
    ``services/approval_service`` stays free of any ``services/audit_service``
    import by depending on the generic ``AsyncAuditWriter`` callable type
    instead.
    """

    async with audit_pool(settings) as pool:

        async def _write(record) -> None:
            await write_audit_event(pool, approval_record_to_audit_event(record))

        yield _write


@asynccontextmanager
async def build_real_calibration_writer(
    settings: Settings,
) -> AsyncIterator[CalibrationWriter]:
    """The real Long-term Memory calibration write path
    (services/memory_service, against ``long_term_memory_calibration`` —
    defined in infrastructure/compose/init/postgres-primary-init.sql).
    Same composition-root reasoning as the two functions above.
    """

    async with calibration_pool(settings) as pool:

        async def _write(events) -> None:
            for event in events:
                await write_calibration_event(pool, event)

        yield _write


@asynccontextmanager
async def build_real_knowledge_backend(
    settings: Settings,
) -> AsyncIterator[DifyAdapter]:
    """Construct a ``DifyAdapter`` from the process-wide settings.

    The adapter is a context manager around an ``httpx.AsyncClient`` —
    this function ensures the client is closed when the Gateway shuts
    down rather than left dangling.

    Configuration comes from ``settings.dify`` (``MARA_DIFY__*`` env vars
    or ``configs/dev/settings.toml`` — see ``shared/config/settings.py``
    ``DifySettings`` for the full list). In development, api_url defaults
    to ``http://localhost:5001/v1``; inside the Docker network it should
    be ``http://dify-api:5001/v1``.

    Dify must be an **internal-only** service — never configure api_url
    to point at an external URL (docs/architecture/11-security-architecture.md
    §11.7).
    """

    async with DifyAdapter(
        api_url=settings.dify.api_url,
        api_key=settings.dify.api_key.get_secret_value(),
        dataset_id=settings.dify.dataset_id,
    ) as adapter:
        yield adapter


@asynccontextmanager
async def build_real_loan_workflow(
    settings: Settings, calibration_writer: CalibrationWriter | None = None
) -> AsyncIterator[ResumableWorkflow]:
    """Construct the real Loan Assessment workflow — all seven agents, six
    approval gates — checkpointed against the primary Postgres instance.

    Same caveat as ``build_real_workflow``: no OCR engine or document
    classifier is wired underneath ``DocumentAgent`` yet, so every request
    fails with a typed ``ToolExternalServiceError`` at the first step until one
    is. That is current platform state, not a fault in this wiring.

    The agents are constructed with their defaults, which means no
    ``KnowledgeBackend`` and no search engine: Compliance falls back to its
    honest NO_POLICY_FOUND path, and Market reports live search unavailable.
    Passing the real Dify adapter and a search engine through here is the next
    step, and deliberately separate — this change is about the workflow being
    reachable at all, and wiring backends in the same commit would make it
    unclear which of the two broke anything that breaks.
    """

    graph = build_loan_assessment_graph(
        DocumentAgent(),
        ComplianceAgent(),
        FinanceAgent(),
        MarketAgent(),
        RiskAgent(),
        RecommendationAgent(),
        calibration_writer=calibration_writer,
    )

    async with postgres_checkpointer(settings) as checkpointer:
        yield graph.compile(checkpointer=checkpointer)
