-- MARA AI-ETC primary Postgres initialization.
-- Enables pgvector for Knowledge Memory (docs/architecture/08-memory-architecture.md)
-- and creates the audit schema with time-range partitioning from day one
-- (docs/architecture/review/03-data-and-security-review.md Finding C1,
-- docs/governance/architecture-approval-report.md §5) rather than retrofitting
-- partitioning after the table has grown.

CREATE EXTENSION IF NOT EXISTS vector;

-- Audit Memory: append-only, immutable, never deleted (docs/architecture/
-- 08-memory-architecture.md §8.2). Partitioned by month so this high-volume
-- table never shares index-maintenance cost with the hot-path tables below.
CREATE TABLE IF NOT EXISTS audit_memory (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    workflow_id     UUID,
    actor_id        TEXT NOT NULL,
    actor_role      TEXT NOT NULL,
    event_type      TEXT NOT NULL, -- tool_call | agent_dispatch | approval | rejection | correction | escalation | permission_check
    payload         JSONB NOT NULL,
    PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);

CREATE INDEX IF NOT EXISTS idx_audit_memory_workflow_id ON audit_memory (workflow_id);
CREATE INDEX IF NOT EXISTS idx_audit_memory_actor_id ON audit_memory (actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_memory_event_type ON audit_memory (event_type);

-- First partition (current month) so the table is usable immediately;
-- a scheduled job (docs/architecture/13-deployment-architecture.md) creates
-- subsequent monthly partitions ahead of time in staging/production.
CREATE TABLE IF NOT EXISTS audit_memory_default PARTITION OF audit_memory DEFAULT;

-- LangGraph's PostgresSaver (shared/workflow_engine/checkpointer.py) creates
-- its own checkpoint tables on first use via `PostgresSaver.setup()` — not
-- created here, since their schema is owned by the langgraph-checkpoint-postgres
-- library, not by MARA AI-ETC, and should not be hand-maintained in this file.
