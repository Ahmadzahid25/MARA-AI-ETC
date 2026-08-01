# Strategi Backup — MARA AI-ETC (Per-Cawangan)

**Versi**: 1.0
**Tarikh**: 2026-07-30
**Rujukan**: [docs/architecture/18-per-branch-database-schema.md](../docs/architecture/18-per-branch-database-schema.md)

---

## 1. Gambaran Keseluruhan

Platform MARA AI-ETC menggunakan **9 instance PostgreSQL berasingan** (8 cawangan + 1 national). Setiap database memerlukan strategi backup mandiri — backup satu cawangan tidak menjamin cawangan lain.

**Prinsip**: pengasingan backup selaras dengan pengasingan data — backup cawangan Selangor tidak bercampur dengan Kelantan.

## 2. Piawaian Backup

| Aspek | Standard |
|---|---|
| Format | `pg_dump --format=custom` (`.dump`, terkompres, restoreSelective) |
| Alat | `docker exec <container> pg_dump` (dalam kontena, tiada pemasangan klien pada hos) |
| Jadual | Harian 02:00 (cron) |
| Retention | 7 harian + 4 mingguan (Ahad) + 12 bulanan (1hb) |
| Lokasi | `/var/backups/mara/{daily,weekly,monthly}/` pada pelayan Proxmox |
| Pembolehubah | `DB_PASSWORD` dibaca dari `.env` (gitignored) atau pembolehubah persekitaran |

## 3. Senarai Database & Port

| Cawangan | Kontena | Port | Database |
|---|---|---|---|
| HQ | `mara-postgres-hq` | 5432 | `mara_hq` |
| Selangor | `mara-postgres-sel` | 5433 | `mara_sel` |
| Kelantan | `mara-postgres-kel` | 5434 | `mara_kel` |
| Johor | `mara-postgres-joh` | 5435 | `mara_joh` |
| Perak | `mara-postgres-prk` | 5436 | `mara_prk` |
| Terengganu | `mara-postgres-trg` | 5437 | `mara_trg` |
| N. Sembilan | `mara-postgres-nsn` | 5438 | `mara_nsn` |
| Kedah | `mara-postgres-kdh` | 5439 | `mara_kdh` |
| National | `mara-postgres-national` | 5440 | `mara_national` |

## 4. Pelaksanaan

### 4.1 Backup Harian (Automatik)

Skrip: [`scripts/backup/backup_all_branches.sh`](../scripts/backup/backup_all_branches.sh)

Cron pada pelayan Proxmox/Ubuntu:

```bash
# /etc/cron.d/mara-backup
0 2 * * * root /opt/mara-ai-etc/scripts/backup/backup_all_branches.sh /var/backups/mara >> /var/log/mara-backup.log 2>&1
```

### 4.2 Restore

Skrip: [`scripts/backup/restore_branch.sh`](../scripts/backup/restore_branch.sh)

```bash
./scripts/backup/restore_branch.sh sel /var/backups/mara/daily/mara_sel_2026-07-30.dump
```

> Restore memerlukan pengesahan interaktif (`ya`) dan akan menggantikan data sedia ada.

### 4.3 Backup Manual (Pemecahan)

Untuk satu cawangan sahaja:

```bash
docker exec mara-postgres-sel pg_dump -U mara -d mara_sel -Fc --no-owner --no-privileges \
    > /var/backups/mara/daily/mara_sel_manual_$(date +%Y%m%d).dump
```

## 5. DR (Disaster Recovery) — Cadangan

Fasa seterusnya (migrasi data belum diputuskan):
1. **Replika luar talian**: rsync backup harian ke NAS/storage berasingan (offsite).
2. **Uji restore**: latihan DR bulanan — restore satu cawangan ke kontena ujian dan sahkan integriti.
3. **PITR**: pertimbangkan WAL archiving untuk point-in-time recovery selepas kestabilan operasi.
4. **Verifikasi checksum**: `pg_restore --list` + saiz fail sebagai pemeriksaan asas.

## 6. Pemantauan

- Log backup: `/var/log/mara-backup.log`
- Skrip mengembalikan kod keluar bukan-sifar jika ada database gagal — sesuaikan dengan河南 monitoring (Prometheus alert berdasarkan cron exit code).
- Saiz backup <-- harian --> jangkauan: setiap dump biasanya < 50 MB pada permulaan; pantau pertumbuhan.

## 7. Migrasi Data

Status: **belum diputuskan**. Apabila data sedia ada dikenalpasti:
- Nilaikan skala dan format sumber.
- Tulis skrip ETL khusus per-cawangan.
- Uji pada cawangan perintis (Selangor) sebelum rollout.