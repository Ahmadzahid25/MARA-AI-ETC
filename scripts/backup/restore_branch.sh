#!/usr/bin/env bash
# MARA AI-ETC — Restore database cawangan dari fail backup.
# docs/architecture/18-per-branch-database-schema.md — strategi backup.
#
# Penggunaan:
#   ./scripts/backup/restore_branch.sh <kod_cawangan> <fail_backup.dump>
# Contoh:
#   ./scripts/backup/restore_branch.sh sel /var/backups/mara/daily/mara_sel_2026-07-30.dump
#
# AMARAN: Restore akan MENGGANTIKAN data sedia ada dalam database tersebut.
# Pastikan kontena sedang berjalan dan database sudah di-init.

set -euo pipefail

if [ "$#" -lt 2 ]; then
    echo "Penggunaan: $0 <kod_cawangan> <fail_backup.dump>"
    echo "Contoh:     $0 sel /var/backups/mara/daily/mara_sel_2026-07-30.dump"
    exit 1
fi

BRANCH_CODE="$1"
BACKUP_FILE="$2"
DB_NAME="mara_${BRANCH_CODE}"
CONTAINER="mara-postgres-${BRANCH_CODE}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "❌ Fail backup tidak wujud: ${BACKUP_FILE}"
    exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -q "${CONTAINER}"; then
    echo "❌ Kontena ${CONTAINER} tidak berjalan. Mulakan dahulu:"
    echo "   docker compose -f infrastructure/compose/branches/docker-compose.branch.yml --env-file infrastructure/compose/branches/.env.${BRANCH_CODE} up -d"
    exit 1
fi

echo "============================================================"
echo "🔄 MEMULIHAKAN ${DB_NAME}"
echo "   Fail:      ${BACKUP_FILE}"
echo "   Kontena:   ${CONTAINER}"
echo "⚠️  AMARAN: Data sedia ada dalam ${DB_NAME} akan diganti!"
echo "============================================================"
read -p "Teruskan? (taip 'ya' untuk sahkan): " CONFIRM
if [ "${CONFIRM}" != "ya" ]; then
    echo "Dibatalkan."
    exit 0
fi

# Drop & recreate schema untuk elak konflik (data diganti sepenuhnya)
echo "🗑️  Membersih database sedia ada..."
docker exec "${CONTAINER}" psql -U mara -d "${DB_NAME}" -c "
    DROP SCHEMA public CASCADE;
    CREATE SCHEMA public;
"

# Restore dari fail custom-format dump
echo "📥 Memulihakan data..."
docker exec -i "${CONTAINER}" pg_restore -U mara -d "${DB_NAME}" --no-owner --no-privileges --clean --if-exists \
    < "${BACKUP_FILE}"

# Verifikasi — kira jadual utama
TABLE_COUNT=$(docker exec "${CONTAINER}" psql -U mara -d "${DB_NAME}" -t -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public';")
echo "============================================================"
echo "✅ Restore ${DB_NAME} selesai — ${TABLE_COUNT} jadual dipulihakan."
echo "============================================================"