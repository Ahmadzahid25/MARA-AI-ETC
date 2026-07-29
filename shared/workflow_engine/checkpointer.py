"""LangGraph Postgres checkpointer wiring.

See docs/architecture/07-workflow-architecture.md §7.6.

This is what makes a workflow instance survive a process restart and resume
on any worker: every stage transition is a checkpoint persisted here, not
held only in process memory. docs/architecture/review/01-architecture-and-
foundation-review.md §3.1 flags checkpoint schema versioning across
langgraph-checkpoint-postgres upgrades as a real operational hazard — pin the
library version in pyproject.toml (already done) and re-run the checkpoint-
resume drill in docs/architecture/14-roadmap.md before bumping it.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from shared.config import Settings


@asynccontextmanager
async def postgres_checkpointer(
    settings: Settings,
) -> AsyncIterator[AsyncPostgresSaver]:
    """Yields a ready-to-use AsyncPostgresSaver against the platform's
    *primary* Postgres instance — never Dify's (see docs/architecture/
    09-knowledge-architecture.md §9.1.1; ACCB Condition C-5). Workflow
    checkpoints are platform state, not knowledge-base state.

    Call ``await saver.setup()`` once (idempotent) before first use in a
    fresh environment — this creates langgraph-checkpoint-postgres' own
    checkpoint tables, which are intentionally NOT hand-defined in
    infrastructure/compose/init/postgres-primary-init.sql (that schema is
    owned by the library, not by MARA AI-ETC).
    """

    dsn = str(settings.database.primary_dsn).replace(
        'postgresql+asyncpg://', 'postgresql://'
    )
    async with AsyncPostgresSaver.from_conn_string(dsn) as saver:
        await saver.setup()
        yield saver


async def ensure_checkpoint_schema(settings: Settings) -> None:
    """Idempotent one-time schema setup. Safe to call on every service
    startup (Milestone 0 Gateway does this) — ``setup()`` no-ops if the
    checkpoint tables already exist.
    """

    async with postgres_checkpointer(settings) as saver:
        await saver.setup()
