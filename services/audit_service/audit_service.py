"""Audit Service — docs/architecture/05-agent-architecture.md §5.11.3:

    "Structured, deterministic query API over Audit Memory for the common
    case (what happened, when, by whom)... Reads: Audit Memory (read-only,
    separate credential path). Writes: nothing to any operational memory —
    its own invocations are themselves audit-logged by the platform."

Writes to and reads from the ``audit_memory`` table
(infrastructure/compose/init/postgres-primary-init.sql) — append-only,
partitioned by month, never updated or deleted
(docs/architecture/08-memory-architecture.md §8.3: "no code path... that
removes an Audit Memory row"). This module is the *only* place that table
is written to or read from — every other component that needs to record an
event goes through ``write_audit_event()``, not raw SQL of its own.

The narrative-summarization layer §5.11.3 also describes is not implemented
here yet — this slice is the structured query API, the "primary,
authoritative" output; the optional LLM narrative layer on top is a
follow-up, not a precondition for the structured API being useful on its
own.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal

import asyncpg
from pydantic import BaseModel, Field

from shared.config import Settings

EventType = Literal[
    'tool_call',
    'agent_dispatch',
    'approval',
    'rejection',
    'correction',
    'escalation',
    'permission_check',
]


class AuditEvent(BaseModel):
    """One row of ``audit_memory``. ``id``/``occurred_at`` are ``None`` on
    a not-yet-written event (set by the database on insert, per the
    table's ``GENERATED ALWAYS AS IDENTITY`` / ``DEFAULT now()``)."""

    id: int | None = None
    occurred_at: datetime | None = None
    workflow_id: str | None = None
    actor_id: str = Field(min_length=1)
    actor_role: str = Field(min_length=1)
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)


class AuditQueryFilters(BaseModel):
    workflow_id: str | None = None
    actor_id: str | None = None
    event_type: EventType | None = None
    since: datetime | None = None
    until: datetime | None = None
    limit: int = Field(default=100, ge=1, le=1000)


@asynccontextmanager
async def audit_pool(settings: Settings) -> AsyncIterator[asyncpg.Pool]:
    """A connection pool against the *primary* Postgres instance — Audit
    Memory is platform state, never Dify's database (ACCB Condition C-5,
    the same separation shared/workflow_engine/checkpointer.py enforces for
    workflow checkpoints)."""

    dsn = str(settings.database.primary_dsn).replace(
        'postgresql+asyncpg://', 'postgresql://'
    )
    pool = await asyncpg.create_pool(dsn)
    try:
        yield pool
    finally:
        await pool.close()


async def write_audit_event(pool: asyncpg.Pool, event: AuditEvent) -> None:
    """Append one event. Insert-only by construction — there is no
    update/delete function in this module to call, which is what makes
    "was this ever altered" unanswerable-by-design rather than a policy
    promise (docs/architecture/08-memory-architecture.md §8.3)."""

    await pool.execute(
        """
        INSERT INTO audit_memory
            (workflow_id, actor_id, actor_role, event_type, payload)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        """,
        event.workflow_id,
        event.actor_id,
        event.actor_role,
        event.event_type,
        json.dumps(event.payload),
    )


async def query_audit_events(
    pool: asyncpg.Pool, filters: AuditQueryFilters
) -> list[AuditEvent]:
    """The "structured event list, primary and authoritative" per §5.11.3.
    Time-range + workflow-ID + actor-ID filterable, matching
    docs/architecture/08-memory-architecture.md §8.4's stated indexing.
    """

    conditions: list[str] = []
    params: list[Any] = []

    def _add(column_expr: str, value: Any) -> None:
        params.append(value)
        conditions.append(f'{column_expr} = ${len(params)}')

    if filters.workflow_id is not None:
        _add('workflow_id', filters.workflow_id)
    if filters.actor_id is not None:
        _add('actor_id', filters.actor_id)
    if filters.event_type is not None:
        _add('event_type', filters.event_type)
    if filters.since is not None:
        params.append(filters.since)
        conditions.append(f'occurred_at >= ${len(params)}')
    if filters.until is not None:
        params.append(filters.until)
        conditions.append(f'occurred_at <= ${len(params)}')

    where_clause = f'WHERE {" AND ".join(conditions)}' if conditions else ''
    params.append(filters.limit)
    query = f"""
        SELECT id, occurred_at, workflow_id, actor_id, actor_role, event_type, payload
        FROM audit_memory
        {where_clause}
        ORDER BY occurred_at DESC
        LIMIT ${len(params)}
    """

    rows = await pool.fetch(query, *params)
    return [_row_to_event(row) for row in rows]


def _row_to_event(row: asyncpg.Record) -> AuditEvent:
    payload = row['payload']
    return AuditEvent(
        id=row['id'],
        occurred_at=row['occurred_at'],
        workflow_id=str(row['workflow_id']) if row['workflow_id'] is not None else None,
        actor_id=row['actor_id'],
        actor_role=row['actor_role'],
        event_type=row['event_type'],
        payload=json.loads(payload) if isinstance(payload, str) else payload,
    )
