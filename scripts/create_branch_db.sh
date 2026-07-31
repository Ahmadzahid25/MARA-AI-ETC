#!/usr/bin/env bash
# MARA AI-ETC — Cipta database cawangan baharu dalam < 5 minit.
# docs/architecture/18-per-branch-database-schema.md §8.
#
# Penggunaan:
#   ./scripts/create_branch_db.sh <kod_cawangan> <nama_cawangan> <port>
# Contoh:
#   ./scripts/create_branch_db.sh prk "Cawangan Perak" 5436
#
# Prerequisites: Docker + docker compose dipasang pada pelayan Proxmox/Ubuntu.

set -euo pipefail

if [ "$#" -lt 3 ]; then
    echo "Penggunaan: $0 <kod_cawangan> <nama_cawangan> <port>"
    echo "Contoh:     $0 prk \"Cawangan Perak\" 5436"
    exit 1
fi

BRANCH_CODE="$1"
BRANCH_NAME="$2"
PORT="$3"

# Kata laluan DB — dibaca dari persekitaran atau fail .env sedia ada.
# Jika tidak ditetapkan, jana satu secara rawak.
if [ -z "${DB_PASSWORD:-}" ]; then
    if [ -f infrastructure/compose/branches/.env ]; then
        DB_PASSWORD=$(grep -E '^DB_PASSWORD=' infrastructure/compose/branches/.env | cut -d= -f2-)
    fi
fi
if [ -z "${DB_PASSWORD:-}" ]; then
    DB_PASSWORD=$(openssl rand -base64 24)
    echo "⚠️  DB_PASSWORD tidak ditemui — jana rawak: $DB_PASSWORD"
    echo "   Simpan nilai ini dalam infrastructure/compose/branches/.env.${BRANCH_CODE}"
fi

ENV_FILE="infrastructure/compose/branches/.env.${BRANCH_CODE}"

echo "============================================================"
echo "🔧 Mencipta database untuk ${BRANCH_NAME} (${BRANCH_CODE})"
echo "   Port: ${PORT}"
echo "   Kata laluan: (tersembunyi)"
echo "============================================================"

# 1. Cipta fail .env cawangan (jika belum wujud)
if [ ! -f "${ENV_FILE}" ]; then
    # URL-encode @ sebagai %40 dalam DSN
    URL_PASS=$(printf '%s' "${DB_PASSWORD}" | sed 's/@/%40/g; s/:/%3A/g; s=/=%2F=g')
    cat > "${ENV_FILE}" << EOF
# .env.${BRANCH_CODE} — ${BRANCH_NAME}
# FAIL INI DI-GITIGNORE — jangan commit.
BRANCH_CODE=${BRANCH_CODE}
BRANCH_NAME="${BRANCH_NAME}"
PORT_PRIMARY=${PORT}
DB_PASSWORD=${DB_PASSWORD}
MARA_DATABASE__PRIMARY_DSN=postgresql+asyncpg://mara:${URL_PASS}@localhost:${PORT}/mara_${BRANCH_CODE}
MARA_BRANCH_CODE=${BRANCH_CODE}
EOF
    echo "✅ Dicipta: ${ENV_FILE}"
else
    echo "ℹ️  ${ENV_FILE} sedia wujud — menggunakan nilai sedia ada."
    # Muat semula DB_PASSWORD dari fail .env supaya seeding一致
    DB_PASSWORD=$(grep -E '^DB_PASSWORD=' "${ENV_FILE}" | cut -d= -f2-)
fi

# 2. Jalankan kontena Docker untuk cawangan ini sahaja
echo "🐳 Memulakan kontena postgres-${BRANCH_CODE}..."
docker compose \
  -p "${BRANCH_CODE}" \
  --env-file "${ENV_FILE}" \
  -f infrastructure/compose/branches/docker-compose.branch.yml \
  up -d "postgres-branch"

# 3. Tunggu database siap (healthcheck)
echo "⏳ Menunggu database siap..."
MAX_WAIT=60
WAITED=0
until docker exec "mara-postgres-${BRANCH_CODE}" pg_isready -U mara -d "mara_${BRANCH_CODE}" &>/dev/null; do
    sleep 2
    WAITED=$((WAITED + 2))
    if [ "${WAITED}" -ge "${MAX_WAIT}" ]; then
        echo "❌ Database tidak sedia selepas ${MAX_WAIT}s. Semak log:"
        docker logs "mara-postgres-${BRANCH_CODE}" --tail 20
        exit 1
    fi
done
echo "✅ Database sedia."

# 4. Isi maklumat cawangan dalam branch_info (seeding)
echo "📝 Menyemai branch_info..."
docker exec "mara-postgres-${BRANCH_CODE}" psql -U mara -d "mara_${BRANCH_CODE}" -c \
  "INSERT INTO branch_info (branch_code, branch_name, state)
   VALUES ('${BRANCH_CODE}', '${BRANCH_NAME}', '${BRANCH_NAME}')
   ON CONFLICT (branch_code) DO NOTHING;"

# 5. Ringkasan
echo "============================================================"
echo "✅ Database cawangan ${BRANCH_NAME} berjaya dicipta!"
echo "   Kontena:    mara-postgres-${BRANCH_CODE}"
echo "   Port:       ${PORT}"
echo "   Database:   mara_${BRANCH_CODE}"
echo "   Fail .env:  ${ENV_FILE}"
echo "   DSN:        postgresql+asyncpg://mara:***@localhost:${PORT}/mara_${BRANCH_CODE}"
echo "============================================================"