-- ═══════════════════════════════════════════════════════════════
-- TEMPLATE SKEMA: mara_national
-- Database nasional MARA AI-ETC untuk laporan, KPI, dan analisis
-- agregat cross-cawangan (docs/architecture/18-per-branch-database-schema.md §5).
--
-- Cawangan TIDAK menulis terus ke sini. Data dimasukkan oleh proses
-- batch sync HQ (cron job) yang membaca dari setiap database cawangan.
-- ─═════════════════════════════════════════════════════════════

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────
-- JADUAL 1: Agregat Permohonan Per-Cawangan (bulanan)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS national_applications_summary (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    branch_code         TEXT NOT NULL,
    period_month        DATE NOT NULL,  -- Bulan laporan (YYYY-MM-01)
    total_applications  INTEGER NOT NULL DEFAULT 0,
    approved_count      INTEGER NOT NULL DEFAULT 0,
    rejected_count      INTEGER NOT NULL DEFAULT 0,
    pending_count      INTEGER NOT NULL DEFAULT 0,
    total_amount_approved NUMERIC(18, 2) NOT NULL DEFAULT 0,
    avg_processing_days NUMERIC(6, 2),
    UNIQUE (branch_code, period_month)
);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 2: KPI Ejen AI Per-Cawangan (bulanan)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS national_agent_kpi (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    branch_code         TEXT NOT NULL,
    period_month        DATE NOT NULL,
    agent_name          TEXT NOT NULL,
    workflows_processed INTEGER NOT NULL DEFAULT 0,
    avg_confidence      DOUBLE PRECISION,
    correction_rate     DOUBLE PRECISION,  -- % yang diperbetulkan oleh pegawai
    UNIQUE (branch_code, period_month, agent_name)
);

CREATE INDEX IF NOT EXISTS idx_agent_kpi_branch_month
    ON national_agent_kpi (branch_code, period_month);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 3: Indeks Risiko Agregat (bulanan)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS national_risk_index (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    branch_code         TEXT NOT NULL,
    period_month        DATE NOT NULL,
    high_risk_count     INTEGER NOT NULL DEFAULT 0,
    medium_risk_count   INTEGER NOT NULL DEFAULT 0,
    low_risk_count      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (branch_code, period_month)
);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 4: Log Sync Batch (jejak setiap proses sync)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS national_sync_log (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    branch_code         TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('SUCCESS', 'PARTIAL', 'FAILED')),
    rows_synced         INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    duration_seconds    NUMERIC(10, 2)
);

CREATE INDEX IF NOT EXISTS idx_sync_log_branch ON national_sync_log (branch_code, synced_at DESC);