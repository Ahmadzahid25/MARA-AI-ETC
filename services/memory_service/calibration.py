"""Long-term Memory — confidence-calibration tracking. docs/architecture/
08-memory-architecture.md §8.2:

    "Long-term Memory: ... an agent's calibration history (how often its
    confidence scores were subsequently overridden) ... Structured
    key-value + periodic batch analysis (e.g., confidence calibration
    reports feeding Phase 12 observability) ... Versioned snapshots, not
    raw overwrite, so calibration drift is analyzable over time."

Pulled into Milestone 1 by the same governance requirement that pulled in
the Compliance Agent stub — the ACCB approval report accepts LLM
self-reported confidence as inherently uncalibrated (Review Board R-A5) "on
condition that the Long-term Memory calibration-tracking loop is actually
built and actively monitored from Milestone 1 onward, not treated as a
nice-to-have" (docs/governance/architecture-approval-report.md §5). This is
that loop's write/query half — the "periodic batch analysis" reporting
layer on top (feeding Phase 12 observability) is a follow-up, not a
precondition for raw events being captured starting now.

Writes to ``long_term_memory_calibration`` — **not yet created** in
infrastructure/compose/init/postgres-primary-init.sql as of this module's
authorship; see infrastructure/AGENTS.md item 8 for the exact DDL handed to
the developer who owns that file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime

import asyncpg
from pydantic import BaseModel, Field

from shared.config import Settings


class CalibrationEvent(BaseModel):
    """One extracted field's confidence, and whether an officer
    subsequently corrected it — the raw signal, per field, that calibration
    drift is computed from. ``id``/``recorded_at`` are ``None`` before the
    database assigns them on insert."""

    id: int | None = None
    recorded_at: datetime | None = None
    agent_name: str = Field(min_length=1)
    workflow_id: str | None = None
    field_name: str = Field(min_length=1)
    document_type: str | None = None
    stated_confidence: float = Field(ge=0.0, le=1.0)
    was_corrected: bool


class CalibrationStats(BaseModel):
    """Aggregated calibration read for one agent (optionally narrowed to
    one field name) — "how often its confidence scores were subsequently
    overridden," per §8.2. A high ``correction_rate`` despite a high
    ``average_stated_confidence`` is exactly the miscalibration pattern
    R-A5 warns about: the agent is confident and wrong, not just uncertain.
    """

    agent_name: str
    field_name: str | None
    total_events: int
    corrected_events: int
    average_stated_confidence: float | None
    average_confidence_when_corrected: float | None

    @property
    def correction_rate(self) -> float | None:
        if self.total_events == 0:
            return None
        return self.corrected_events / self.total_events


@asynccontextmanager
async def calibration_pool(settings: Settings) -> AsyncIterator[asyncpg.Pool]:
    """A connection pool against the *primary* Postgres instance — Long-term
    Memory is platform state, never Dify's database (ACCB Condition C-5,
    the same separation ``shared/workflow_engine/checkpointer.py`` and
    ``services/audit_service`` enforce)."""

    dsn = str(settings.database.primary_dsn).replace(
        'postgresql+asyncpg://', 'postgresql://'
    )
    pool = await asyncpg.create_pool(dsn)
    try:
        yield pool
    finally:
        await pool.close()


async def write_calibration_event(pool: asyncpg.Pool, event: CalibrationEvent) -> None:
    """Append one calibration event. Insert-only — per §8.2, calibration
    history is "versioned snapshots, not raw overwrite," and an
    append-only events table is what makes drift-over-time analyzable
    without a separate versioning mechanism bolted on."""

    await pool.execute(
        """
        INSERT INTO long_term_memory_calibration
            (agent_name, workflow_id, field_name, document_type,
             stated_confidence, was_corrected)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        event.agent_name,
        event.workflow_id,
        event.field_name,
        event.document_type,
        event.stated_confidence,
        event.was_corrected,
    )


async def query_calibration_stats(
    pool: asyncpg.Pool, agent_name: str, field_name: str | None = None
) -> CalibrationStats:
    """Aggregate calibration stats for one agent, optionally narrowed to a
    single field name — the "periodic batch analysis" read side of §8.2,
    kept as a live aggregate query for now rather than a scheduled
    materialization job (a reasonable simplification at current expected
    event volume; revisit if the table grows large enough that this query
    becomes the bottleneck)."""

    conditions = ['agent_name = $1']
    params: list[object] = [agent_name]
    if field_name is not None:
        params.append(field_name)
        conditions.append(f'field_name = ${len(params)}')
    where_clause = ' AND '.join(conditions)

    row = await pool.fetchrow(
        f"""
        SELECT
            count(*) AS total_events,
            count(*) FILTER (WHERE was_corrected) AS corrected_events,
            avg(stated_confidence) AS average_stated_confidence,
            avg(stated_confidence) FILTER (WHERE was_corrected)
                AS average_confidence_when_corrected
        FROM long_term_memory_calibration
        WHERE {where_clause}
        """,
        *params,
    )

    return CalibrationStats(
        agent_name=agent_name,
        field_name=field_name,
        total_events=row['total_events'],
        corrected_events=row['corrected_events'],
        average_stated_confidence=row['average_stated_confidence'],
        average_confidence_when_corrected=row['average_confidence_when_corrected'],
    )
