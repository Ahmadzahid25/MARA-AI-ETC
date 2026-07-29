#!/usr/bin/env bash
# MARA AI-ETC — Automated Remote Server Deployment Script
# Usage: bash scripts/deploy_server.sh

set -euo pipefail

echo "============================================================"
echo "🚀 MARA AI-ETC — Automated Server Deployment Initializing..."
echo "============================================================"

# 1. System Requirements & Dependency Check
echo "🔍 [1/5] Checking system prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "📦 Docker not found. Installing Docker Engine..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker "$USER" || true
    rm get-docker.sh
fi

if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose plugin is missing. Please install docker-compose-plugin."
    exit 1
fi

echo "✅ Docker & Docker Compose are available."

# 2. Environment Configuration
echo "⚙️ [2/5] Setting up production environment configuration..."

if [ ! -f .env.production ]; then
    cat <<'EOF' > .env.production
# MARA AI-ETC Server Environment Configuration
MARA_ENVIRONMENT=production
KEYCLOAK_ADMIN=admin
KEYCLOAK_ADMIN_PASSWORD=MaraProduction2026!Secret
POSTGRES_USER=mara
POSTGRES_PASSWORD=MaraDBSecret2026!
MINIO_ROOT_USER=mara-prod
MINIO_ROOT_PASSWORD=MaraMinioProdSecret2026!
SECRET_KEY=production_secret_key_mara_ai_etc_2026_change_me
VITE_API_GATEWAY_URL=http://localhost:8051
EOF
    echo "📝 Created .env.production with production secret defaults."
else
    echo "ℹ️ Using existing .env.production"
fi

# 3. Launch Docker Infrastructure Stack
echo "🐳 [3/5] Launching MARA AI-ETC Docker Stack (All 4 Layers)..."

docker compose \
  --env-file .env.production \
  -f docker-compose.yml \
  -f infrastructure/compose/docker-compose.mara.yml \
  -f infrastructure/compose/docker-compose.observability.yml \
  -f infrastructure/compose/docker-compose.dify.yml \
  up -d

echo "✅ Docker containers launched successfully."

# 4. Build Officer Workspace Frontend
echo "🏗️ [4/5] Building Officer Workspace Frontend SPA..."

if command -v npm &> /dev/null; then
    (
      cd apps/officer-workspace
      npm install
      npm run build
    )
    echo "✅ Officer Workspace built successfully -> apps/officer-workspace/dist/"
else
    echo "⚠️ npm not found on server host. Building via node docker container..."
    docker run --rm -v "$(pwd):/app" -w /app/apps/officer-workspace node:22-alpine sh -c "npm install && npm run build"
    echo "✅ Officer Workspace built via Docker -> apps/officer-workspace/dist/"
fi

# 5. Summary & Health Status
echo "============================================================"
echo "🎉 MARA AI-ETC Deployment Completed Successfully!"
echo "============================================================"
echo ""
echo "Endpoints:"
echo "  - Keycloak SSO:          http://localhost:8080"
echo "  - Postgres Primary:      localhost:5432"
echo "  - Redis:                 localhost:6379"
echo "  - MinIO Storage:         http://localhost:9000 (Console: :9001)"
echo "  - Langfuse Observability: http://localhost:3300"
echo "  - Dify Knowledge Stack:  http://localhost:5001"
echo ""
echo "To start API Gateway Backend:"
echo "  poetry run python -m services.api_gateway.main"
echo ""
echo "To serve Officer Workspace Frontend:"
echo "  Use NGINX / Caddy pointing to $(pwd)/apps/officer-workspace/dist"
echo "============================================================"
