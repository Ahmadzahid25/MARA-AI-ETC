# infrastructure/compose/

Local-dev orchestration for MARA AI-ETC's own services, additive alongside the root `docker-compose.yml` (OpenHands' own — never edited in place, see [`docs/repo-audit/06-openhands-protection-rules.md`](../../docs/repo-audit/06-openhands-protection-rules.md) §6.1).

**Status: written but not yet run or verified in this environment** — Docker was not available when this scaffold was created (Milestone 0). Validate with `docker compose config` and a local `up` before relying on it, and treat the Keycloak realm secrets (`REPLACE_ME_DEV_ONLY`) and Langfuse dev secrets as exactly that — dev-only placeholders, never used outside a local machine.

## Bring up the full local stack

```bash
docker compose \
  -f docker-compose.yml \
  -f infrastructure/compose/docker-compose.mara.yml \
  -f infrastructure/compose/docker-compose.observability.yml \
  -f infrastructure/compose/docker-compose.dify.yml \
  up -d
```

| File | Provides |
|---|---|
| `docker-compose.mara.yml` | `postgres-primary` (pgvector, Audit Memory partitioned from day one), `postgres-dify` (separate instance — ACCB Condition C-5), `redis`, `minio` (+ bucket init), `keycloak` (realm auto-imported from `init/keycloak-realm-mara-ai-etc.json`) |
| `docker-compose.observability.yml` | `otel-collector`, `prometheus`, `loki`, `grafana`, `langfuse` (+ its own Postgres) |
| `docker-compose.dify.yml` | `dify-api`, `dify-worker`, `dify-web` — knowledge/RAG engine (Milestone 2). Runs against `postgres-dify` only (ACCB C-5), no outbound internet (§11.7). Backend wires `DIFY_API_URL=http://dify-api:5001/v1` via `services/knowledge_service`. |

## Ports (dev defaults, matching `configs/dev/settings.toml`)

| Service | Port | Notes |
|---|---|---|
| postgres-primary | 5432 | `mara` / `mara` / `mara_platform` |
| postgres-dify | 5433 | `dify` / `dify` / `dify` — separate instance, not a schema on 5432 |
| redis | 6379 | |
| minio | 9000 (API), 9001 (console) | `mara-dev` / `mara-dev-secret` |
| keycloak | 8080 | `admin` / `admin-dev-only` |
| prometheus | 9090 | |
| grafana | 3000 | `admin` / `admin-dev-only` |
| loki | 3100 | |
| langfuse | 3300 | |
| otel-collector | 4317 (gRPC), 4318 (HTTP) | |
| dify-api | 5001 | `REPLACE_ME_DEV_ONLY` init password — internal URL: `http://dify-api:5001/v1` |
| dify-web | 3001 | Admin UI (host only; 3000 is Grafana) |

Milestone 0's acceptance criterion ("a synthetic end-to-end trace is visible in Grafana/Langfuse," [`docs/architecture/14-roadmap.md`](../../docs/architecture/14-roadmap.md) §14.2) is verified against this stack once it's actually running — this compose scaffold is a precondition for that check, not the check itself.
