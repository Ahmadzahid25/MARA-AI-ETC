# Per-Branch Databases — MARA AI-ETC

Fail compose di direktori ini menjalankan seni bina **satu database per cawangan**
(docs/architecture/18-per-branch-database-schema.md) — 8 database cawangan + 1
database nasional, berbanding satu database `mara_platform` dalam
`../docker-compose.mara.yml` (konfigurasi Milestone 0/1 yang lebih lama).

## ⚠️ PENTING: Dua konfigurasi database yang berasingan — jangan jalankan serentak

Terdapat **dua** cara untuk menyediakan Postgres, dan ia **berkongsi port**:

| Konfigurasi | Fail | Port digunakan | Database |
|---|---|---|---|
| **Lama (Milestone 0/1)** | `../docker-compose.mara.yml` | `5432` (postgres-primary), `5433` (postgres-dify) | `mara_platform`, `dify` |
| **Baharu (per-cawangan)** | `docker-compose.stack.yml` di sini | `5432` (HQ), `5433` (Selangor), … `5439` (Kedah), `5440` (National) | `mara_hq` … `mara_kdh`, `mara_national` |

Kedua-duanya menggunakan port **5432 dan 5433**, jadi anda **tidak boleh**
menjalankan kedua-dua stack serentak pada pelayan yang sama tanpa konflik port.

**Cadangan migration path:**
1. **Fasa peralihan (kini):** Teruskan `docker-compose.mara.yml` untuk kerja
   backend sedia ada (yang masih menunjuk ke `mara_platform`). Uji stack
   cawangan baharu pada **port berbeza** (lihat `.env.hqtest` yang memetakan
   `55432`) untuk pengesahan tanpa mengganggu stack sedia ada.
2. **Cutover:** Apabila backend telah disahkan sepenuhnya terhadap skema
   cawangan, hentikan stack lama (`docker compose -f ../docker-compose.mara.yml down`)
   dan jalankan stack cawangan baharu. Kemas kini `configs/*/settings.toml`
   `primary_dsn` kepada `mara_hq` (atau cawangan yang berkaitan).

## Fail

| Fail | Tujuan |
|---|---|
| `docker-compose.stack.yml` | Jalankan **kesemua 9** database serentak (8 cawangan + national) |
| `docker-compose.branch.yml` | Jalankan **satu** database cawangan (guna `--env-file .env.<kod>`) |
| `env.example` | Contoh konfigurasi `.env` (committed, tanpa rahsia) |
| `.env`, `.env.<kod>` | Kata laluan DB sebenar — **gitignored**, jangan commit |
| `../init/branch-init.sql` | Skema 10 jadual untuk setiap cawangan |
| `../init/national-init.sql` | Skema agregat untuk database nasional |

## Cara guna

### Semua cawangan serentak (pengeluaran / staging)
```bash
docker compose \
  -f infrastructure/compose/branches/docker-compose.stack.yml \
  --env-file infrastructure/compose/branches/.env \
  up -d
```

### Satu cawangan sahaja (dev / ujian)
```bash
# Contoh: HQ sahaja
docker compose -p hq \
  -f infrastructure/compose/branches/docker-compose.branch.yml \
  --env-file infrastructure/compose/branches/.env.hq \
  up -d postgres-branch
```

### Cawangan baharu (< 5 minit)
```bash
./scripts/create_branch_db.sh prk "Cawangan Perak" 5436
```

## Verifikasi
```bash
docker compose -f infrastructure/compose/branches/docker-compose.stack.yml \
  --env-file infrastructure/compose/branches/.env config --quiet
```

**Status:** skema + backend (`AsyncpgVerticalSliceStore`, `audit_service`)
telah diuji secara langsung terhadap database cawangan sebenar (HQ, port
55432) — register, create application, upload dokumen, officer decision, dan
audit trail dengan `branch_code` semuanya berfungsi.