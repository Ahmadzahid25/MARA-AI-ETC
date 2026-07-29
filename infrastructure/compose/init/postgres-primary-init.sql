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

-- Long-term Memory: confidence-calibration tracking (docs/architecture/
-- 08-memory-architecture.md §8.2). One row per extracted field per
-- workflow, recording the agent's stated confidence and whether an
-- officer subsequently corrected it — the raw signal a periodic batch
-- job aggregates into calibration reports. Append-only, like
-- audit_memory, so calibration drift is analyzable over time rather
-- than overwritten.
CREATE TABLE IF NOT EXISTS long_term_memory_calibration (
    id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recorded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_name         TEXT NOT NULL,
    workflow_id        UUID,
    field_name         TEXT NOT NULL,
    document_type      TEXT,
    stated_confidence  DOUBLE PRECISION NOT NULL,
    was_corrected      BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_calibration_agent_field
    ON long_term_memory_calibration (agent_name, field_name);
CREATE INDEX IF NOT EXISTS idx_calibration_workflow_id
    ON long_term_memory_calibration (workflow_id);

-- Vertical-slice v1 relational skeleton (docs/architecture/
-- 17-vertical-slice-execution-directive.md §17.11).
CREATE TABLE IF NOT EXISTS mara_users (
    id                 UUID PRIMARY KEY,
    full_name          TEXT NOT NULL,
    email              TEXT NOT NULL UNIQUE,
    password_hash      TEXT NOT NULL,
    role               TEXT NOT NULL CHECK (role IN ('applicant', 'officer', 'admin')),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS applicants (
    id                 UUID PRIMARY KEY,
    user_id            UUID NOT NULL REFERENCES mara_users(id),
    full_name          TEXT NOT NULL,
    ic_number          TEXT NOT NULL,
    phone              TEXT NOT NULL,
    email              TEXT NOT NULL,
    state              TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS businesses (
    id                 UUID PRIMARY KEY,
    applicant_id       UUID NOT NULL REFERENCES applicants(id),
    business_name      TEXT NOT NULL,
    ssm_number         TEXT NOT NULL,
    sector             TEXT NOT NULL,
    years_operating    INTEGER NOT NULL DEFAULT 0,
    monthly_revenue_avg NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS applications (
    id                 UUID PRIMARY KEY,
    applicant_id       UUID NOT NULL REFERENCES applicants(id),
    business_id        UUID NOT NULL REFERENCES businesses(id),
    scheme             TEXT NOT NULL,
    amount_requested   NUMERIC(14, 2) NOT NULL,
    purpose            TEXT NOT NULL,
    tenure_months      INTEGER NOT NULL,
    status             TEXT NOT NULL CHECK (
        status IN ('DRAFT', 'SUBMITTED', 'PROCESSING', 'NEEDS_INFO', 'UNDER_REVIEW', 'APPROVED', 'REJECTED')
    ),
    ai_assessment      JSONB NOT NULL DEFAULT '{}'::jsonb,
    stage_log          JSONB NOT NULL DEFAULT '[]'::jsonb,
    decided_by         UUID REFERENCES mara_users(id),
    decision_notes     TEXT NOT NULL DEFAULT '',
    decided_at         TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_updated_at ON applications(updated_at DESC);

CREATE TABLE IF NOT EXISTS application_documents (
    id                 UUID PRIMARY KEY,
    application_id     UUID NOT NULL REFERENCES applications(id),
    doc_type           TEXT NOT NULL,
    file_name          TEXT NOT NULL,
    file_path          TEXT NOT NULL,
    mime_type          TEXT NOT NULL,
    ocr_status         TEXT NOT NULL DEFAULT 'PENDING',
    extraction         JSONB NOT NULL DEFAULT '{}'::jsonb,
    completeness       TEXT NOT NULL DEFAULT 'PERLU_PENGESAHAN',
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_application_documents_application_id
    ON application_documents(application_id);

-- LangGraph's PostgresSaver (shared/workflow_engine/checkpointer.py) creates
-- its own checkpoint tables on first use via `PostgresSaver.setup()` — not
-- created here, since their schema is owned by the langgraph-checkpoint-postgres
-- library, not by MARA AI-ETC, and should not be hand-maintained in this file.
