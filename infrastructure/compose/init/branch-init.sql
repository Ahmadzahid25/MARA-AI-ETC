-- ═══════════════════════════════════════════════════════════════
-- TEMPLATE SKEMA: mara_<kod_cawangan>
-- Skema standard untuk setiap database cawangan MARA AI-ETC
-- (docs/architecture/18-per-branch-database-schema.md §3).
--
-- Skrip ini dijalankan oleh Postgres entrypoint pada kontena baharu.
-- Nama database ditentukan oleh POSTGRES_DB dalam docker-compose
-- (cth mara_hq, mara_sel, mara_kel). Tidak perlu CREATE DATABASE di sini.
-- Ganti <BRANCH_CODE> dalam branch_info hanya jika diperlukan —
-- seeding row ditambah oleh skrip create_branch_db.sh selepas init.
-- ═══════════════════════════════════════════════════════════════

-- Aktifkan extension pgvector (carian semantik AI) dan uuid-ossp
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─────────────────────────────────────────────────────────────
-- JADUAL 1: Metadata Cawangan (satu baris sahaja)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS branch_info (
    id              SERIAL PRIMARY KEY,
    branch_code     TEXT NOT NULL UNIQUE,
    branch_name     TEXT NOT NULL,          -- cth: "Cawangan Selangor"
    state           TEXT NOT NULL,          -- cth: "Selangor"
    address         TEXT,
    phone           TEXT,
    email           TEXT,
    head_officer    TEXT,
    activated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_active       BOOLEAN NOT NULL DEFAULT true
);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 2: Pengguna Sistem (Pegawai & Pemohon)
-- Pegawai: login guna Keycloak SSO (keycloak_sub sahaja dirujuk).
-- Pemohon: login guna Nombor IC + password_hash (bcrypt).
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mara_users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_code     TEXT NOT NULL,          -- merujuk kepada branch_info.branch_code
    keycloak_sub    TEXT UNIQUE,            -- ID dari Keycloak (SSO untuk Pegawai)
    ic_number       TEXT UNIQUE,            -- KUNCI UTAMA login pemohon (MyKad). Nullable:
                    -- pendaftaran portal (/api/v1/auth/register) tidak mengumpul IC,
                    -- jadi dibiarkan NULL sehingga pemohon mengisi profil lengkap.
    full_name       TEXT NOT NULL,
    staff_id        TEXT UNIQUE,            -- No. Pekerja MARA (hanya untuk pegawai)
    email           TEXT UNIQUE,            -- E-mel pengguna (opsional/sekunder)
    phone           TEXT,
    password_hash   TEXT,                   -- bcrypt (hanya untuk pemohon)
    role            TEXT NOT NULL CHECK (role IN (
                        'applicant',        -- Pemohon Usahaan
                        'officer',          -- Pegawai Penilaian
                        'senior_officer',   -- Pegawai Kanan / Penyelia
                        'risk_officer',     -- Pegawai Risiko
                        'admin',            -- Pentadbir Cawangan
                        'auditor'           -- Juruaudit
                    )),
    mfa_enrolled    BOOLEAN NOT NULL DEFAULT false,
    last_login_at   TIMESTAMPTZ,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_branch ON mara_users(branch_code);
CREATE INDEX IF NOT EXISTS idx_users_role ON mara_users(role);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 3: Profil Pemohon (Individu/Syarikat)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applicants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES mara_users(id) ON DELETE RESTRICT,
    full_name       TEXT NOT NULL,
    ic_number       TEXT NOT NULL UNIQUE,
    phone           TEXT NOT NULL,
    email           TEXT NOT NULL,
    -- Medan alamat dibuat NULLABLE: borang permohonan v1
    -- (shared/schemas/vertical_slice.py ApplicantProfileInput) tidak mengumpul
    -- alamat — diisi kemudian oleh pemohon / pegawai.
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    postcode        TEXT,
    state           TEXT NOT NULL,
    bumiputera      BOOLEAN NOT NULL DEFAULT true,  -- Syarat kelayakan MARA
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 4: Perniagaan / Syarikat
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS businesses (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    applicant_id            UUID NOT NULL REFERENCES applicants(id) ON DELETE RESTRICT,
    business_name           TEXT NOT NULL,
    ssm_number              TEXT NOT NULL UNIQUE,
    -- business_type dibuat NULLABLE: borang permohonan v1
    -- (shared/schemas/vertical_slice.py BusinessProfileInput) tidak mengumpul
    -- jenis perniagaan — diisi kemudian oleh pemohon / pegawai.
    business_type           TEXT CHECK (business_type IN (
                                'sole_proprietor',  -- Milikan Tunggal
                                'partnership',      -- Perkongsian
                                'sdn_bhd',          -- Syarikat Sdn. Bhd.
                                'bhd',              -- Syarikat Berhad
                                'koperasi'          -- Koperasi
                            )),
    sector                  TEXT NOT NULL,          -- cth: "F&B", "Runcit", "Teknologi"
    subsector               TEXT,
    years_operating         INTEGER NOT NULL DEFAULT 0,
    employee_count          INTEGER NOT NULL DEFAULT 0,
    monthly_revenue_avg     NUMERIC(14, 2) NOT NULL DEFAULT 0,
    monthly_expenses_avg    NUMERIC(14, 2) NOT NULL DEFAULT 0,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 5: Permohonan Pembiayaan
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_no        TEXT NOT NULL UNIQUE,  -- cth: "MARA-SEL-2026-00123"
    applicant_id        UUID NOT NULL REFERENCES applicants(id) ON DELETE RESTRICT,
    business_id         UUID NOT NULL REFERENCES businesses(id) ON DELETE RESTRICT,
    assigned_officer_id UUID REFERENCES mara_users(id),    -- Pegawai yang ditugaskan

    -- Maklumat Skim Pembiayaan
    scheme              TEXT NOT NULL,          -- cth: "MARA Skim Pembiayaan Kontrak (SPiKE)"
    amount_requested    NUMERIC(14, 2) NOT NULL,
    amount_approved     NUMERIC(14, 2),         -- Diisi selepas kelulusan
    purpose             TEXT NOT NULL,
    tenure_months       INTEGER NOT NULL,

    -- Status Alur Kerja
    status              TEXT NOT NULL DEFAULT 'DRAFT' CHECK (
                            status IN (
                                'DRAFT',        -- Draf awal pemohon
                                'SUBMITTED',    -- Diserahkan oleh pemohon
                                'PROCESSING',   -- Sedang diproses oleh AI
                                'NEEDS_INFO',   -- Maklumat tambahan diperlukan
                                'UNDER_REVIEW', -- Dalam semakan pegawai
                                'APPROVED',     -- Diluluskan
                                'REJECTED',     -- Ditolak
                                'WITHDRAWN'     -- Ditarik balik oleh pemohon
                            )
                        ),

    -- Output AI Assessment (JSONB — fleksibel mengikut ejen)
    ai_assessment       JSONB NOT NULL DEFAULT '{}'::jsonb,
    stage_log           JSONB NOT NULL DEFAULT '[]'::jsonb,

    -- Maklumat Keputusan
    decided_by          UUID REFERENCES mara_users(id),
    decision_notes      TEXT NOT NULL DEFAULT '',
    decided_at          TIMESTAMPTZ,

    -- LangGraph Workflow Thread ID (untuk sambung checkpoint)
    workflow_thread_id  UUID UNIQUE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_applications_status ON applications(status);
CREATE INDEX IF NOT EXISTS idx_applications_officer ON applications(assigned_officer_id);
CREATE INDEX IF NOT EXISTS idx_applications_updated ON applications(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_applications_reference ON applications(reference_no);

-- Fungsi auto-generate nombor rujukan cawangan
CREATE OR REPLACE FUNCTION generate_reference_no(branch TEXT)
RETURNS TEXT AS $$
DECLARE
    seq_val BIGINT;
    year_part TEXT;
BEGIN
    year_part := TO_CHAR(NOW(), 'YYYY');
    SELECT COUNT(*) + 1 INTO seq_val
    FROM applications
    WHERE reference_no LIKE 'MARA-' || branch || '-' || year_part || '-%';

    RETURN 'MARA-' || branch || '-' || year_part || '-' || LPAD(seq_val::TEXT, 5, '0');
END;
$$ LANGUAGE plpgsql;

-- ─────────────────────────────────────────────────────────────
-- JADUAL 6: Dokumen Permohonan
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS application_documents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    doc_type        TEXT NOT NULL CHECK (doc_type IN (
                        'IC_COPY',              -- Salinan MyKad
                        'SSM_CERTIFICATE',      -- Sijil Pendaftaran SSM
                        'BANK_STATEMENT',       -- Penyata Bank (6 bulan)
                        'AUDITED_ACCOUNTS',     -- Akaun Beraudit
                        'BUSINESS_PLAN',        -- Pelan Perniagaan
                        'COLLATERAL_DOCS',      -- Dokumen Cagaran
                        'TAX_RETURN',           -- Borang Cukai
                        'OTHER'                 -- Dokumen Lain
                    )),
    file_name       TEXT NOT NULL,
    file_path       TEXT NOT NULL,  -- Path dalam MinIO Object Storage
    mime_type       TEXT NOT NULL,
    file_size_bytes BIGINT,

    -- Status & Hasil OCR/AI
    ocr_status      TEXT NOT NULL DEFAULT 'PENDING' CHECK (
                        ocr_status IN ('PENDING', 'PROCESSING', 'DONE', 'FAILED')
                    ),
    extraction      JSONB NOT NULL DEFAULT '{}'::jsonb,
    completeness    TEXT NOT NULL DEFAULT 'PERLU_PENGESAHAN',

    uploaded_by     UUID REFERENCES mara_users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_docs_application ON application_documents(application_id);
CREATE INDEX IF NOT EXISTS idx_docs_ocr_status ON application_documents(ocr_status);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 7: Pintu Kelulusan (Human Approval Gates)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS approval_gates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id  UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    workflow_thread_id UUID,
    gate_name       TEXT NOT NULL,  -- cth: "confirm_extraction", "recommendation_approval"
    gate_sequence   INTEGER NOT NULL DEFAULT 1,

    -- Status Gate
    status          TEXT NOT NULL DEFAULT 'PENDING' CHECK (
                        status IN ('PENDING', 'APPROVED', 'REJECTED', 'CORRECTED', 'ESCALATED')
                    ),
    assigned_role   TEXT NOT NULL,  -- Peranan yang perlu beri keputusan

    -- Payload & Keputusan
    gate_payload    JSONB NOT NULL DEFAULT '{}'::jsonb,  -- Data AI untuk review
    decision_by     UUID REFERENCES mara_users(id),
    decision_notes  TEXT,
    corrections     JSONB,          -- Pembetulan pegawai (jika ada)

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at      TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_gates_application ON approval_gates(application_id);
CREATE INDEX IF NOT EXISTS idx_gates_status ON approval_gates(status);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 8: Memori Audit (Append-Only — Tidak Boleh Dipadam)
-- Partition mengikut tarikh untuk prestasi jangka panjang.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_memory (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    workflow_id     UUID,
    application_id  UUID,
    actor_id        TEXT NOT NULL,
    actor_role      TEXT NOT NULL,
    branch_code     TEXT NOT NULL,
    -- event_type tidak di-CHECK: backend menulis action string bebas
    -- (cth 'register', 'application_submitted', 'officer_decision',
    -- 'document_uploaded') selain jenis standard 'approval'/'rejection'/
    -- 'correction'. Selaras dengan skema postgres-primary-init.sql yang tidak
    -- mengenakan CHECK pada lajur ini.
    event_type      TEXT NOT NULL,
    payload         JSONB NOT NULL,
    PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);

-- Partition awal (default) supaya jadual boleh diguna terus
CREATE TABLE IF NOT EXISTS audit_memory_default PARTITION OF audit_memory DEFAULT;

CREATE INDEX IF NOT EXISTS idx_audit_workflow ON audit_memory (workflow_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_memory (actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_application ON audit_memory (application_id);
CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_memory (event_type);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 9: Kalibrasi Memori Jangka Panjang (AI Confidence)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS long_term_memory_calibration (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    recorded_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    agent_name          TEXT NOT NULL,
    workflow_id         UUID,
    field_name          TEXT NOT NULL,
    document_type       TEXT,
    stated_confidence   DOUBLE PRECISION NOT NULL,
    was_corrected       BOOLEAN NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_calibration_agent ON long_term_memory_calibration (agent_name, field_name);

-- ─────────────────────────────────────────────────────────────
-- JADUAL 10: Pemberitahuan Dalam Sistem
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_id    UUID NOT NULL REFERENCES mara_users(id),
    application_id  UUID REFERENCES applications(id),
    type            TEXT NOT NULL,  -- cth: "gate_pending", "approved", "needs_info"
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    is_read         BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id, is_read);

-- ─────────────────────────────────────────────────────────────
-- CATATAN: Jadual Checkpoint LangGraph
-- ─────────────────────────────────────────────────────────────
-- Jadual checkpoint LangGraph (checkpoints, checkpoint_blobs,
-- checkpoint_writes) TIDAK dicipta di sini. Ia dicipta secara
-- automatik oleh shared/workflow_engine/checkpointer.py melalui:
--   await saver.setup()
-- apabila API Gateway dimulakan untuk kali pertama.
-- Jadual tersebut dimiliki oleh library langgraph-checkpoint-postgres.