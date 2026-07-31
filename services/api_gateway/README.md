# API Gateway service

Implemented (Milestone 0 scope): correlation-ID middleware, OTel instrumentation, Keycloak JWT bearer authentication, health check, and a synthetic end-to-end trace diagnostic endpoint. See [`02-system-architecture.md`](../../docs/architecture/02-system-architecture.md#22-layer-responsibilities) Â§2.2 for the full layer specification this implements toward.

**Not yet run or verified** â€” this was built without a live Postgres/Keycloak/OTel-collector stack (Docker unavailable at scaffold time). Before trusting it:

1. `docker compose -f docker-compose.yml -f infrastructure/compose/docker-compose.mara.yml -f infrastructure/compose/docker-compose.observability.yml up -d`
2. `uv sync` (regenerates the lockfile with the new `langgraph`, `pydantic-settings`, `opentelemetry-sdk`, etc. dependencies added to `pyproject.toml` â€” not yet run in this environment)
3. For local applicant-portal development without Docker workflows, run `MARA_ENABLE_REAL_WORKFLOWS=0 uv run python -m services.api_gateway.main` (PowerShell: `$env:MARA_ENABLE_REAL_WORKFLOWS='0'; uv run python -m services.api_gateway.main`).
4. `curl localhost:8051/healthz`
5. Obtain a bearer token for a user with the `auditor` realm role from Keycloak (realm imported from `infrastructure/compose/init/keycloak-realm-mara-ai-etc.json`), then `curl -X POST localhost:8051/diagnostics/synthetic-trace -H "Authorization: Bearer <token>"` and confirm the resulting trace/checkpoint is visible in Grafana (port 3000) and Langfuse (port 3300) â€” this is the literal Milestone 0 acceptance check from [`14-roadmap.md`](../../docs/architecture/14-roadmap.md) Â§14.2.

## Files

| File | Purpose |
|---|---|
| `app.py` | FastAPI app factory |
| `main.py` | uvicorn entrypoint |
| `middleware.py` | Correlation-ID assignment/propagation |
| `auth.py` | Keycloak JWT bearer validation (`get_current_principal`, `require_role`) |
| `telemetry.py` | OTel tracer + FastAPI auto-instrumentation |
| `routers/health.py` | Unauthenticated liveness check |
| `routers/diagnostics.py` | Auditor-gated synthetic-trace endpoint |

No business-logic routers yet â€” those arrive from Milestone 1 onward as the agents/services behind them exist (per [`02-system-architecture.md`](../../docs/architecture/02-system-architecture.md) Â§2.2: "No business logic lives here â€” it is a thin, replaceable edge").
