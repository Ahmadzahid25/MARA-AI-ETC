# Pelan Skema Pangkalan Data — MARA AI-ETC (Per-Cawangan)

**Versi**: 1.1  
**Tarikh**: 2026-07-30  
**Status**: Draf untuk Kelulusan  
**Kemaskini**: Ditambah §4 — Aliran Data Login & Permohonan

---

## 1. Gambaran Keseluruhan Seni Bina

### 1.1 Konsep: Setiap Cawangan = Database Sendiri

Setiap cawangan MARA mempunyai **satu instance PostgreSQL berasingan** yang berjalan dalam kontena Docker tersendiri. Reka bentuk ini memastikan:

- **Pengasingan Data Mutlak**: Data cawangan Kelantan tidak boleh dicampur dengan Selangor.
- **Keselamatan & Pematuhan**: Memenuhi keperluan audit kerajaan — data satu cawangan tidak boleh dilihat oleh cawangan lain.
- **Fleksibiliti Penyelenggaraan**: Backup, restore, atau upgrade satu cawangan tidak menjejaskan cawangan lain.
- **Kawalan Beban (Load Control)**: Cawangan sibuk (cth: HQ KL) tidak menjejaskan prestasi cawangan kecil.

### 1.2 Model Pengasingan 3-Peringkat

```
┌─────────────────────────────────────────────────────────┐
│                  MARA AI-ETC PLATFORM                   │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  HQ Putera   │  │  Selangor    │  │   Kelantan   │  │
│  │  Jaya        │  │  Cawangan    │  │   Cawangan   │  │
│  │              │  │              │  │              │  │
│  │ Postgres:    │  │ Postgres:    │  │ Postgres:    │  │
│  │ mara_hq_kl   │  │ mara_sel     │  │ mara_kel     │  │
│  │ Port: 5432   │  │ Port: 5433   │  │ Port: 5434   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  POSTGRES GLOBAL (Peringkat Nasional/Laporan)    │   │
│  │  mara_national — Agregat, KPI, Cross-Branch      │   │
│  │  Port: 5440 — Read-only replicas per cawangan    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Senarai Cawangan MARA

Berikut adalah cawangan yang telah dikenalpasti untuk fasa pertama:

| Kod Cawangan | Nama Penuh | Kod DB | Port |
|---|---|---|---|
| `HQ` | Ibu Pejabat (Putrajaya/KL) | `mara_hq` | `5432` |
| `SEL` | Cawangan Selangor | `mara_sel` | `5433` |
| `KEL` | Cawangan Kelantan | `mara_kel` | `5434` |
| `JOH` | Cawangan Johor | `mara_joh` | `5435` |
| `PRK` | Cawangan Perak | `mara_prk` | `5436` |
| `TRG` | Cawangan Terengganu | `mara_trg` | `5437` |
| `NSN` | Cawangan Negeri Sembilan | `mara_nsn` | `5438` |
| `KDH` | Cawangan Kedah | `mara_kdh` | `5439` |
| `NATIONAL` | Pangkalan Data Nasional (Agregat) | `mara_national` | `5440` |

> ⚠️ **Nota**: Tambah cawangan baharu mengikut senarai rasmi MARA. Port boleh dikonfigurasi semula mengikut keperluan infrastruktur.

---

## 3. Skema Pangkalan Data Setiap Cawangan

Setiap cawangan menggunakan **skema yang sama** (template), hanya nama database yang berbeza. Ini memudahkan penyelenggaraan dan kemaskini.

### 3.1 Jadual-Jadual Utama (Per-Cawangan)

```sql
-- ═══════════════════════════════════════════════════════════════
-- TEMPLATE SKEMA: mara_<kod_cawangan>
-- Digunakan untuk setiap cawangan. Ganti <BRANCH_CODE> dengan
-- kod cawangan semasa (cth: hq, sel, kel, joh, prk, trg, nsn, kdh)
-- ═══════════════════════════════════════════════════════════════

-- Aktifkan extension pgvector (carian semantik AI)
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
-- JADUAL 2: Pengguna Sistem (Pegawai & Pentadbir Cawangan)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS mara_users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    branch_code     TEXT NOT NULL,          -- merujuk kepada branch_info.branch_code
    keycloak_sub    TEXT UNIQUE,            -- ID dari Keycloak (SSO)
    full_name       TEXT NOT NULL,
    ic_number       TEXT NOT NULL UNIQUE,
    staff_id        TEXT NOT NULL UNIQUE,   -- No. Pekerja MARA
    email           TEXT NOT NULL UNIQUE,
    phone           TEXT,
    role            TEXT NOT NULL CHECK (role IN (
                        'applicant',        -- Pemohon (dari Portal Pemohon)
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
    address_line1   TEXT NOT NULL,
    address_line2   TEXT,
    city            TEXT NOT NULL,
    postcode        TEXT NOT NULL,
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
    business_type           TEXT NOT NULL CHECK (business_type IN (
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
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_memory (
    id              BIGINT GENERATED ALWAYS AS IDENTITY,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    workflow_id     UUID,
    application_id  UUID,
    actor_id        TEXT NOT NULL,
    actor_role      TEXT NOT NULL,
    branch_code     TEXT NOT NULL,
    event_type      TEXT NOT NULL CHECK (event_type IN (
                        'tool_call',
                        'agent_dispatch',
                        'approval',
                        'rejection',
                        'correction',
                        'escalation',
                        'permission_check',
                        'login',
                        'document_upload',
                        'status_change'
                    )),
    payload         JSONB NOT NULL,
    PRIMARY KEY (id, occurred_at)
) PARTITION BY RANGE (occurred_at);

-- Partition awal (bulan semasa)
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
-- Jadual checkpoint LangGraph (checkpoints, checkpoint_blobs, checkpoint_writes)
-- TIDAK dicipta di sini. Ia dicipta secara automatik oleh
-- shared/workflow_engine/checkpointer.py melalui:
--   await saver.setup()
-- apabila API Gateway dimulakan untuk kali pertama.
-- Jadual tersebut dimiliki oleh library langgraph-checkpoint-postgres.
```

---

## 4. Aliran Data — Login Pengguna & Permohonan

Terdapat **dua jenis pengguna** dalam sistem MARA AI-ETC dengan mekanisme login yang berbeza. Data mereka disimpan di tempat yang berbeza berdasarkan peranan.

### 4.1 Jenis Pengguna & Sistem Login

| Jenis Pengguna | Mekanisme Login | Di Mana Data Login Disimpan | Di Mana Profil Disimpan |
|---|---|---|---|
| **Pegawai MARA** (Officer, Senior Officer, Risk Officer, Admin, Auditor) | SSO Keycloak (OIDC/JWT RS256) | **Keycloak DB** — berasingan, diurus oleh Keycloak | `mara_users` (cawangan) — hanya simpan `keycloak_sub` sebagai rujukan |
| **Pemohon Usahawan** | API terus (`/api/v1/auth/login`) | `mara_users.password_hash` (bcrypt) dalam DB cawangan | `mara_users` + `applicants` (cawangan) |

> **Prinsip Keselamatan**: Kata laluan pegawai **TIDAK PERNAH** disimpan dalam database MARA. Ia diurus sepenuhnya oleh Keycloak. MARA hanya menyimpan `keycloak_sub` (ID unik Keycloak) sebagai rujukan.

---

### 4.2 Aliran Login Pegawai MARA (SSO Keycloak)

```
┌────────────────────────────────────────────────────────────────────┐
│                    PEGAWAI MARA — ALIRAN LOGIN                     │
│                                                                    │
│  LoginPage.tsx                                                     │
│      │                                                             │
│      │  Klik "Sign in with SSO (Keycloak Server)"                  │
│      ▼                                                             │
│  [Keycloak OIDC] ────────────────────────────────────────────────► │
│      │  Pegawai masuk kata laluan di halaman Keycloak              │
│      │  (bukan di MARA — Keycloak yang verify kata laluan)         │
│      │                                                             │
│      │  Token JWT (RS256) dikembalikan                             │
│      ▼                                                             │
│  services/api_gateway/auth.py                                      │
│      │  Verify token RS256 / HS256 (dev mode)                     │
│      │  Extract: sub, email, roles, branch_code                   │
│      │                                                             │
│      ▼                                                             │
│  mara_<cawangan> Database                                          │
│  ┌──────────────────────────────────────┐                          │
│  │  mara_users (role='officer')         │                          │
│  │   - keycloak_sub  ← ID dari Keycloak │  ← Disimpan di sini     │
│  │   - staff_id                         │                          │
│  │   - role, branch_code                │                          │
│  │   - last_login_at (dikemaskini)      │                          │
│  │   TIADA password_hash di sini        │                          │
│  └──────────────────────────────────────┘                          │
│                                                                    │
│  Log audit login:                                                  │
│  ┌──────────────────────────────────────┐                          │
│  │  audit_memory                        │                          │
│  │   - event_type: 'login'              │                          │
│  │   - actor_id: keycloak_sub           │                          │
│  │   - actor_role: 'officer'            │                          │
│  └──────────────────────────────────────┘                          │
└────────────────────────────────────────────────────────────────────┘
```

---

### 4.3 Aliran Daftar & Login Pemohon Usahawan

```
┌────────────────────────────────────────────────────────────────────┐
│                  PEMOHON USAHAWAN — DAFTAR AKAUN                   │
│                                                                    │
│  ApplicantPortalPage.tsx (halaman /applicant)                      │
│      │                                                             │
│      │  POST /api/v1/auth/register                                 │
│      │  { full_name, email, password }                             │
│      ▼                                                             │
│  mara_<cawangan> Database                                          │
│  ┌──────────────────────────────────────────┐                      │
│  │  mara_users (role='applicant')           │                      │
│  │   - id (UUID)                            │                      │
│  │   - email                                │  ← Disimpan di sini  │
│  │   - password_hash  ← bcrypt (tidak plain)│                      │
│  │   - full_name                            │                      │
│  │   - branch_code  ← cawangan pemohon      │                      │
│  └──────────────────────────────────────────┘                      │
│                                                                    │
│  ─────────────────────────────────────────────────────────         │
│                                                                    │
│  POST /api/v1/auth/login                                           │
│  { email, password }                                               │
│      │                                                             │
│      │  Verify bcrypt → Jana JWT token HS256                       │
│      │  Token dikembalikan ke frontend                             │
│      ▼                                                             │
│  ApplicantPortalPage.tsx menyimpan token dalam sessionStorage      │
│  Semua request seterusnya guna: Authorization: Bearer <token>      │
└────────────────────────────────────────────────────────────────────┘
```

---

### 4.4 Aliran Penuh Permohonan Pembiayaan (End-to-End)

```
PEMOHON                          DATABASE (mara_<cawangan>)
   │
   ├─ [1] Daftar Akaun ─────────► mara_users (role='applicant')
   │       email, password_hash       ↳ id, email, bcrypt hash
   │
   ├─ [2] Isi Profil Peribadi ──► applicants
   │       nama, IC, telefon,         ↳ ic_number, phone
   │       alamat, negeri              ↳ address, state
   │                                  ↳ bumiputera=true/false
   │
   ├─ [3] Maklumat Perniagaan ──► businesses
   │       nama syarikat, SSM,        ↳ ssm_number, sector
   │       sektor, pendapatan          ↳ monthly_revenue_avg
   │
   ├─ [4] Hantar Permohonan ────► applications
   │       skim, jumlah,              ↳ reference_no: "MARA-SEL-2026-00001"
   │       tempoh, tujuan             ↳ status: 'SUBMITTED'
   │                                  ↳ workflow_thread_id (LangGraph UUID)
   │
   ├─ [5] Upload Dokumen ───────► application_documents
   │       PDF SSM, bank,            ↳ file_path → MinIO s3://mara-docs/sel/
   │       penyata, IC               ↳ ocr_status: 'PENDING'
   │
   └─ [6] Semak Status ─────────► applications.status + stage_log
           (Real-time tracker)        ↳ 'PROCESSING' → 'UNDER_REVIEW'


─── SISTEM AI BERJALAN SECARA AUTOMATIK ──────────────────────────────

LangGraph Workflow                   DATABASE (mara_<cawangan>)
   │
   ├─ Document Agent ───────────► application_documents.extraction
   │   OCR & ekstraksi                ↳ ocr_status: 'DONE'
   │
   ├─ Compliance Agent ─────────► applications.ai_assessment (JSONB)
   │   Semak dasar MARA               ↳ {"compliance": {"status": "pass"}}
   │
   ├─ Finance Agent ────────────► applications.ai_assessment (JSONB)
   │   Analisis kewangan              ↳ {"finance": {"ratio": 1.2}}
   │
   ├─ Market Agent ─────────────► applications.ai_assessment (JSONB)
   │   Trend pasaran                  ↳ {"market": {"sector_growth": "5%"}}
   │
   ├─ Risk Agent ───────────────► applications.ai_assessment (JSONB)
   │   Skor risiko                    ↳ {"risk": {"rating": "low"}}
   │
   ├─ Recommendation Agent ─────► approval_gates (JEDA DI SINI)
   │   Syor akhir                     ↳ gate_name: 'recommendation_approval'
   │                                  ↳ status: 'PENDING'
   │                                  ↳ gate_payload: {syor lengkap AI}
   │
   └─ Checkpoint disimpan ──────► langgraph_checkpoints (auto)
       (setiap peringkat)            ↳ Boleh resume bila-bila masa


─── PEGAWAI MARA BUAT KEPUTUSAN ─────────────────────────────────────

PEGAWAI                          DATABASE (mara_<cawangan>)
   │
   ├─ Terima notifikasi ────────► notifications
   │   (gate menunggu kelulusan)     ↳ type: 'gate_pending'
   │
   ├─ Review Console ───────────► approval_gates.gate_payload
   │   Semak syor AI                  ↳ Papar output semua ejen
   │
   ├─ Buat Keputusan ───────────► approval_gates.status = 'APPROVED'
   │   Approve / Reject / Correct     ↳ decision_by = pegawai UUID
   │                               ► applications.status = 'APPROVED'
   │                                  ↳ decided_by, decided_at
   │
   └─ Log Audit (auto) ─────────► audit_memory (TIDAK BOLEH DIPADAM)
                                    ↳ event_type: 'approval'
                                    ↳ actor_id, payload lengkap
```

---

### 4.5 Di Mana Setiap Data Disimpan — Jadual Ringkasan

| Data | Jadual / Sistem | Teknologi | Boleh Padam? |
|---|---|---|---|
| Kata laluan Pegawai | **Keycloak DB** (berasingan) | PostgreSQL Keycloak | Oleh Keycloak admin |
| Profil Pegawai | `mara_users` (cawangan) | PostgreSQL | Ya (deactivate sahaja) |
| Kata laluan Pemohon | `mara_users.password_hash` (cawangan) | bcrypt + PostgreSQL | Ya |
| Profil Pemohon | `applicants` (cawangan) | PostgreSQL | Tidak (rekod permohonan) |
| Maklumat Perniagaan | `businesses` (cawangan) | PostgreSQL | Tidak |
| Permohonan Pembiayaan | `applications` (cawangan) | PostgreSQL | Tidak |
| Fail PDF & Dokumen | MinIO Object Storage | S3-compatible | Ya (dengan kelulusan) |
| Hasil OCR & AI | `application_documents.extraction` | JSONB dalam PostgreSQL | Tidak |
| Output Ejen AI | `applications.ai_assessment` | JSONB dalam PostgreSQL | Tidak |
| Checkpoint Workflow | `langgraph_checkpoints` (cawangan) | PostgreSQL (auto) | Tidak |
| Pintu Kelulusan | `approval_gates` (cawangan) | PostgreSQL | Tidak |
| Log Audit | `audit_memory` (cawangan) | PostgreSQL (partition) | **Tidak Sama Sekali** |
| Pemberitahuan | `notifications` (cawangan) | PostgreSQL | Ya (selepas dibaca) |
| KPI Nasional | `mara_national` (HQ) | PostgreSQL | Ya (data agregat) |

---

## 5. Pangkalan Data Nasional (Agregat Cross-Cawangan)

Database `mara_national` digunakan oleh HQ untuk laporan nasional & KPI. Data ditulis oleh proses batch (bukan secara langsung oleh cawangan).

```sql
-- DATABASE: mara_national
-- Hanya untuk laporan, KPI, dan analisis agregat.
-- Cawangan TIDAK menulis terus ke sini.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Agregat Permohonan Per-Cawangan
CREATE TABLE IF NOT EXISTS national_applications_summary (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    synced_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    branch_code         TEXT NOT NULL,
    period_month        DATE NOT NULL,  -- Bulan laporan (YYYY-MM-01)
    total_applications  INTEGER NOT NULL DEFAULT 0,
    approved_count      INTEGER NOT NULL DEFAULT 0,
    rejected_count      INTEGER NOT NULL DEFAULT 0,
    pending_count       INTEGER NOT NULL DEFAULT 0,
    total_amount_approved NUMERIC(18, 2) NOT NULL DEFAULT 0,
    avg_processing_days NUMERIC(6, 2),
    UNIQUE (branch_code, period_month)
);

-- KPI Ejen AI Per-Cawangan
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

-- Indeks Risiko Agregat
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
```

---

## 6. Fail Docker Compose Per-Cawangan

### 6.1 Template `docker-compose.branch.yml`

```yaml
# Template Docker Compose untuk SATU cawangan.
# Salin dan ubah nilai BRANCH_CODE, BRANCH_NAME, PORT_PRIMARY.

services:
  postgres-${BRANCH_CODE}:
    image: pgvector/pgvector:pg16
    container_name: mara-postgres-${BRANCH_CODE}
    restart: unless-stopped
    environment:
      POSTGRES_USER: mara
      POSTGRES_PASSWORD: ${DB_PASSWORD}          # Dari .env — JANGAN hardcode!
      POSTGRES_DB: mara_${BRANCH_CODE}
    ports:
      - "${PORT_PRIMARY}:5432"
    volumes:
      - mara_data_${BRANCH_CODE}:/var/lib/postgresql/data
      - ./infrastructure/compose/init/branch-init.sql:/docker-entrypoint-initdb.d/01-init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mara -d mara_${BRANCH_CODE}"]
      interval: 10s
      timeout: 5s
      retries: 10
    labels:
      mara.branch: "${BRANCH_CODE}"
      mara.component: "database"

volumes:
  mara_data_${BRANCH_CODE}:
    driver: local
```

### 6.2 Contoh Fail `.env` Per-Cawangan

```bash
# .env.sel — Cawangan Selangor
BRANCH_CODE=sel
BRANCH_NAME="Cawangan Selangor"
PORT_PRIMARY=5433
DB_PASSWORD=<kata_laluan_selamat_sel>

# Konfigurasi API Gateway untuk cawangan ini
MARA_DATABASE__PRIMARY_DSN=postgresql+asyncpg://mara:${DB_PASSWORD}@localhost:${PORT_PRIMARY}/mara_${BRANCH_CODE}
MARA_BRANCH_CODE=sel
```

---

## 7. Konfigurasi Backend (settings.py) — Sokongan Multi-Cawangan

Perubahan diperlukan pada `shared/config/settings.py` untuk menambah konfigurasi cawangan:

```python
class BranchSettings(BaseSettings):
    """Konfigurasi khusus cawangan."""
    code: str = Field(
        default='hq',
        description='Kod cawangan (hq, sel, kel, joh, prk, trg, nsn, kdh)',
    )
    name: str = Field(default='Ibu Pejabat')
    state: str = Field(default='Wilayah Persekutuan')

class DatabaseSettings(BaseSettings):
    primary_dsn: PostgresDsn = Field(
        default='postgresql+asyncpg://mara:mara@localhost:5432/mara_hq',
        description='DSN pangkalan data cawangan semasa.',
    )
    national_dsn: PostgresDsn | None = Field(
        default=None,
        description='DSN pangkalan data nasional (hanya untuk HQ & Laporan).',
    )
    dify_dsn: PostgresDsn = Field(
        default='postgresql+asyncpg://dify:dify@localhost:5433/dify',
    )

class Settings(BaseSettings):
    # ... (fields sedia ada) ...
    branch: BranchSettings = Field(default_factory=BranchSettings)
```

---

## 8. Skrip Automasi Cipta Database Cawangan Baharu

Skrip ini membolehkan penambahan cawangan baharu dalam masa **< 5 minit**:

```bash
#!/bin/bash
# scripts/create_branch_db.sh
# Penggunaan: ./scripts/create_branch_db.sh <kod_cawangan> <nama_cawangan> <port>
# Contoh:     ./scripts/create_branch_db.sh prk "Cawangan Perak" 5436

BRANCH_CODE=$1
BRANCH_NAME=$2
PORT=$3

echo "Mencipta database untuk $BRANCH_NAME ($BRANCH_CODE) pada port $PORT..."

# 1. Cipta fail .env cawangan
cat > .env.${BRANCH_CODE} << EOF
BRANCH_CODE=${BRANCH_CODE}
BRANCH_NAME="${BRANCH_NAME}"
PORT_PRIMARY=${PORT}
DB_PASSWORD=$(openssl rand -base64 24)
MARA_DATABASE__PRIMARY_DSN=postgresql+asyncpg://mara:\${DB_PASSWORD}@localhost:${PORT}/mara_${BRANCH_CODE}
MARA_BRANCH_CODE=${BRANCH_CODE}
EOF

# 2. Jalankan kontena Docker
docker compose \
  --env-file .env.${BRANCH_CODE} \
  -f infrastructure/compose/docker-compose.branch.yml \
  up -d postgres-${BRANCH_CODE}

# 3. Tunggu database siap
echo "Menunggu database siap..."
sleep 10

# 4. Isi maklumat cawangan
docker exec mara-postgres-${BRANCH_CODE} psql -U mara -d mara_${BRANCH_CODE} -c \
  "INSERT INTO branch_info (branch_code, branch_name, state) VALUES ('${BRANCH_CODE}', '${BRANCH_NAME}', '${BRANCH_NAME}');"

echo "✅ Database cawangan $BRANCH_NAME berjaya dicipta!"
echo "   Port: $PORT"
echo "   Database: mara_${BRANCH_CODE}"
```

---

## 9. Aliran Data Antara Cawangan & Nasional

```
┌─────────────────────────────────────────────────────────────────┐
│                        ALIRAN DATA                              │
│                                                                 │
│  Cawangan SEL          Cawangan KEL          Cawangan JOH       │
│  mara_sel              mara_kel              mara_joh            │
│      │                     │                     │              │
│      └─────────────────────┼─────────────────────┘              │
│                            │                                    │
│                    (Batch Sync — setiap malam)                  │
│                            ▼                                    │
│                    mara_national (HQ)                           │
│                    - KPI per cawangan                           │
│                    - Laporan nasional                           │
│                    - Analisis risiko agregat                    │
└─────────────────────────────────────────────────────────────────┘
```

**Peraturan Data**:
- ✅ Cawangan **menulis** ke database sendiri sahaja.
- ✅ Cawangan **membaca** dari database sendiri sahaja (untuk operasi harian).
- ✅ Proses batch HQ **membaca** dari semua cawangan untuk laporan nasional.
- ❌ Cawangan **TIDAK BOLEH** menulis atau membaca data cawangan lain secara langsung.

---

## 10. Rancangan Pelaksanaan (Fasa)

### Fasa 1 — Asas (Minggu 1-2)
- [ ] Siapkan `branch-init.sql` (skrip SQL template lengkap per cawangan)
- [ ] Siapkan `docker-compose.branch.yml` (template Docker Compose)
- [ ] Cipta `scripts/create_branch_db.sh` (skrip automasi)
- [ ] Kemaskini `settings.py` untuk sokongan multi-cawangan (`BranchSettings`)
- [ ] Uji dengan 2 cawangan: HQ + 1 cawangan (cth: Selangor)

### Fasa 2 — Integrasi (Minggu 3-4)
- [ ] Kemaskini API Gateway untuk baca `MARA_BRANCH_CODE` dari `.env`
- [ ] Kemaskini nombor rujukan permohonan: `MARA-{BRANCH}-{YEAR}-{SEQ}`
- [ ] Kemaskini audit log untuk sertakan `branch_code` dalam setiap rekod
- [ ] Uji workflow penuh (OCR → AI Assessment → Kelulusan) per cawangan

### Fasa 3 — Laporan Nasional (Minggu 5-6)
- [ ] Cipta database `mara_national` dengan skema agregat
- [ ] Bina skrip batch sync (Python / cron job) untuk tarik data dari cawangan ke nasional
- [ ] Bina dashboard laporan nasional dalam Admin Console HQ

### Fasa 4 — Rollout (Minggu 7-8)
- [ ] Rollout ke semua 8 cawangan
- [ ] Latihan pegawai
- [ ] Monitor dan penalaan prestasi

---

## 11. Soalan Terbuka untuk Kelulusan

> [!IMPORTANT]
> Perkara-perkara berikut perlu keputusan sebelum pelaksanaan boleh dimulakan:

1. **Senarai Cawangan Rasmi**: Adakah 8 cawangan dalam jadual §2 tepat? Perlu senarai lengkap dari MARA.
2. **Infrastruktur Pelayan**: Adakah setiap cawangan ada pelayan Proxmox tersendiri, atau semua kongsi 1 pelayan? Ini menentukan sama ada kita guna 1 pelayan dengan banyak port, atau banyak pelayan masing-masing dengan port 5432.
3. **Kata Laluan Database**: Siapa yang urus dan simpan kata laluan database per-cawangan? Perlu Vault (HashiCorp Vault) atau simpan dalam Keycloak Secrets?
4. **Backup Strategy**: Berapa kerap backup diperlukan? Siapa yang bertanggungjawab untuk restore jika berlaku kegagalan?
5. **Data Migration**: Adakah ada data sedia ada yang perlu dipindahkan ke skema baharu ini?
