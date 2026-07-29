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

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
import asyncpg

from services.api_gateway.middleware import CorrelationIdMiddleware
from services.api_gateway.routers import (
    approvals,
    chat,
    diagnostics,
    documents,
    health,
    loans,
    vertical_slice,
)
from services.api_gateway.telemetry import instrument_app
from services.api_gateway.vertical_slice_store import (
    AsyncpgVerticalSliceStore,
    InMemoryVerticalSliceStore,
    seed_default_users,
)
from services.approval_service.approval_service import (
    AsyncAuditWriter,
    ResumableWorkflow,
)
from shared.config import get_settings

_UNSET = object()


def create_app(
    workflow: ResumableWorkflow | None = None,
    audit_writer: AsyncAuditWriter | None | object = _UNSET,
    loan_workflow: ResumableWorkflow | None = None,
) -> FastAPI:
    """``workflow``: the compiled Document Assessment workflow graph.
    Tests pass one directly (e.g. compiled with ``InMemorySaver``). Left
    unset in production — the real one is built lazily at startup by
    ``composition.py`` (a documented, narrow exception to the services/
    dependency rule; see that module) against the real Postgres
    checkpointer, since it needs an open connection for the app's lifetime.

    ``audit_writer``: the real Audit Memory writer. Distinguishes "not
    passed" (``_UNSET`` — build the real one alongside ``workflow`` in
    production) from "explicitly ``None``" (a test deliberately exercising
    the structured-logging fallback) — plain ``None`` as the default
    wouldn't let tests express that second case.
    """

    settings = get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.vertical_slice_store = InMemoryVerticalSliceStore()

        if workflow is not None or loan_workflow is not None:
            # Test/injection path. Either graph may be supplied alone — a test
            # exercising the loan endpoints has no reason to also build a
            # Document Assessment graph, and vice versa. The unset one is left
            # absent rather than stubbed, so touching its routes raises rather
            # than silently operating on a placeholder.
            if workflow is not None:
                app.state.workflow = workflow
            if loan_workflow is not None:
                app.state.loan_workflow = loan_workflow
            app.state.audit_writer = None if audit_writer is _UNSET else audit_writer
            yield
            return

        if settings.mode in {'dev', 'staging', 'production'}:
            use_db_store = settings.debug or settings.mode != 'dev'
            if use_db_store:
                dsn = str(settings.database.primary_dsn).replace(
                    'postgresql+asyncpg://', 'postgresql://'
                )
                try:
                    pool = await asyncpg.create_pool(dsn)
                except Exception:
                    pool = None
                if pool is not None:
                    app.state.vertical_slice_store = AsyncpgVerticalSliceStore(pool)

                    async def _close_pool() -> None:
                        await pool.close()

                    app.state._close_vertical_slice_pool = _close_pool

                await seed_default_users(app.state.vertical_slice_store)

        from services.api_gateway.composition import (
            build_real_audit_writer,
            build_real_calibration_writer,
            build_real_loan_workflow,
            build_real_workflow,
        )

        # calibration_writer is baked into the compiled graph at
        # construction time (workflows/document_assessment closes over it),
        # not looked up per-request like audit_writer — so it must be
        # entered before build_real_workflow, not alongside it.
        async with (
            build_real_calibration_writer(settings) as real_calibration_writer,
            build_real_audit_writer(settings) as real_audit_writer,
        ):
            async with (
                build_real_workflow(
                    settings, calibration_writer=real_calibration_writer
                ) as real_workflow,
                build_real_loan_workflow(
                    settings, calibration_writer=real_calibration_writer
                ) as real_loan_workflow,
            ):
                app.state.workflow = real_workflow
                app.state.loan_workflow = real_loan_workflow
                app.state.audit_writer = real_audit_writer
                yield

        close_pool = getattr(app.state, '_close_vertical_slice_pool', None)
        if close_pool is not None:
            await close_pool()

    app = FastAPI(
        title='MARA AI-ETC API Gateway',
        description='Single entry point for all officer-workspace traffic. '
        'See docs/architecture/02-system-architecture.md §2.2.',
        version='0.1.0-milestone1',
        lifespan=lifespan,
    )

    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=['*'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )

    # Ensure request-time dependencies can resolve in tests that instantiate
    # TestClient without entering lifespan context.
    app.state.vertical_slice_store = InMemoryVerticalSliceStore()

    app.add_middleware(CorrelationIdMiddleware)
    instrument_app(app, settings)

    app.include_router(health.router)
    app.include_router(diagnostics.router)
    app.include_router(documents.router)
    app.include_router(approvals.router)
    app.include_router(loans.router)
    app.include_router(chat.router)
    app.include_router(vertical_slice.router)

    return app
