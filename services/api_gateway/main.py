"""Uvicorn entrypoint. Run locally with:

    uv run uvicorn services.api_gateway.main:app --reload --port 8000

(after
    docker compose -f docker-compose.yml \
      -f infrastructure/compose/docker-compose.mara.yml \
      -f infrastructure/compose/docker-compose.observability.yml up -d
 — the Gateway expects Postgres, Keycloak, and the OTel collector reachable.)
"""

from __future__ import annotations

from services.api_gateway.app import create_app

app = create_app()
