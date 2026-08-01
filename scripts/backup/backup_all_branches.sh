#!/usr/bin/env bash
# MARA AI-ETC — Backup semua database cawangan + national.
# docs/architecture/18-per-branch-database-schema.md — strategi backup.
#
# Menjalankan pg_dump (format custom, terkompres) untuk setiap database
# cawangan dan national. Retention: 7 harian + 4 mingguan + 12 bulanan.
#
# Penggunaan:
#   ./scripts/backup/backup_all_branches.sh [backup_dir]
#
# Cron (setiap hari 02:00):
#   0 2 * * * /opt/mara-ai-etc/scripts/backup/backup_all_branches.sh /var/backups/mara >> /var/log/mara-backup.log 2>&1
#
# Prerequisites: Docker + kontena database MARA berjalan.

set -euo pipefail

# Senarai cawangan + port (mesti sepadan dengan docker-compose.stack.yml)
BRANCHES=(
    "hq:5432"
    "sel:5433"
    "kel:5434"
    "joh:5435"
    "prk:5436"
    "trg:5437"
    "nsn:5438"
    "kdh:5439"
    "national:5440"
)

BACKUP_DIR="${1:-/var/backups/mara}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DATE=$(date +%Y-%m-%d)
DB_PASSWORD="${DB_PASSWORD:-}"

# Baca DB_PASSWORD dari master .env jika tidak ditetapkan
if [ -z "${DB_PASSWORD}" ] && [ -f infrastructure/compose/branches/.env ]; then
    DB_PASSWORD=$(grep -E '^DB_PASSWORD=' infrastructure/compose/branches/.env | cut -d= -f2-)
fi

if [ -z "${DB_PASSWORD}" ]; then
    echo "❌ DB_PASSWORD tidak ditemui. Tetapkan pembolehubah persekitaran atau cipta .env."
    exit 1
fi

mkdir -p "${BACKUP_DIR}/daily" "${BACKUP_DIR}/weekly" "${BACKUP_DIR}/monthly"

echo "============================================================"
echo "💾 MARA AI-ETC — Backup bermula pada ${TIMESTAMP}"
echo "   Destinasi: ${BACKUP_DIR}"
echo "============================================================"

FAILED=0

for entry in "${BRANCHES[@]}"; do
    BRANCH_CODE="${entry%%:*}"
    PORT="${entry##*:}"
    DB_NAME="mara_${BRANCH_CODE}"
    CONTAINER="mara-postgres-${BRANCH_CODE}"
    BACKUP_FILE="${BACKUP_DIR}/daily/${DB_NAME}_${DATE}.dump"

    echo "📦 Membackup ${DB_NAME} (port ${PORT})..."

    # Semak kontena berjalan
    if ! docker ps --format '{{.Names}}' | grep -q "${CONTAINER}"; then
        echo "   ⚠️  Kontena ${CONTAINER} tidak berjalan — langkau."
        FAILED=$((FAILED + 1))
        continue
    fi

    # pg_dump dalam format custom (terkompres, boleh restoreSelective)
    if docker exec "${CONTAINER}" pg_dump -U mara -d "${DB_NAME}" -Fc --no-owner --no-privileges \
        > "${BACKUP_FILE}" 2>/dev/null; then
        SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
        echo "   ✅ ${BACKUP_FILE} (${SIZE})"
    else
        echo "   ❌ Gagal backup ${DB_NAME}"
        rm -f "${BACKUP_FILE}"
        FAILED=$((FAILED + 1))
        continue
    fi

    # Replika mingguan (Ahad) dan bulanan (1hb)
    DOW=$(date +%u)   # 1=Isnin, 7=Ahad
    DOM=$(date +%-d)
    if [ "${DOW}" = "7" ]; then
        cp -f "${BACKUP_FILE}" "${BACKUP_DIR}/weekly/${DB_NAME}_week_$(date +%Y-W%V).dump"
        echo "   📅 Replika mingguan dicipta."
    fi
    if [ "${DOM}" = "1" ]; then
        cp -f "${BACKUP_FILE}" "${BACKUP_DIR}/monthly/${DB_NAME}_$(date +%Y-%m).dump"
        echo "   📅 Replika bulanan dicipta."
    fi
done

# Gandeng retention: 7 harian, 4 mingguan, 12 bulanan
echo "🧹 Membersih backup lama..."
find "${BACKUP_DIR}/daily"   -name "*.dump" -mtime +7   -delete 2>/dev/null || true
find "${BACKUP_DIR}/weekly"  -name "*.dump" -mtime +28  -delete 2>/dev/null || true
find "${BACKUP_DIR}/monthly" -name "*.dump" -mtime +365 -delete 2>/dev/null || true

echo "============================================================"
if [ "${FAILED}" -eq 0 ]; then
    echo "✅ Semua backup berjaya pada ${TIMESTAMP}"
else
    echo "⚠️  ${FAILED} backup gagal — semak log."
fi
echo "============================================================"
exit ${FAILED}