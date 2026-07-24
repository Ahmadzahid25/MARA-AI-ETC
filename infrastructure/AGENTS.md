# infrastructure/ — AI agent brief (read this before every task)

You own **infrastructure and deployment**. This file is your boundary and
your map. Read it fully before touching anything, every session — don't
rely on memory from a previous session.

## Hard boundary — read this part twice

**You touch files under `infrastructure/`, `containers/`, `kind/`, and the
deployment-related parts of `.github/workflows/` — and nowhere else.**
Specifically:

- ❌ **Never** edit anything under `agents/`, `tools/`, `services/`,
  `workflows/`, `shared/`, `apps/officer-workspace/`. Those are
  backend/AI-agent and frontend code, owned by other people on this team.
  If a task seems to require changing one of those, **stop and flag it** —
  don't work around it by duplicating logic into infrastructure config.
- ❌ **Never** edit `openhands/` outside sanctioned integration points —
  see [`docs/repo-audit/06-openhands-protection-rules.md`](../docs/repo-audit/06-openhands-protection-rules.md).
  The root `docker-compose.yml` is OpenHands' own — never edit it in place;
  MARA additions are separate, additive compose files (see below).
- ❌ **Never** edit `.github/workflows/mara-ci.yml` (lint/test for
  `agents/`/`tools/`/`services/`/`workflows/`/`shared/` — someone else's
  gate) — your CI surface is deployment pipelines, a separate concern.
- ✅ Your write scope: `infrastructure/**`, `containers/**`, `kind/**`,
  new deployment-specific GitHub Actions workflows.

## What this system is (read before touching any infra config)

MARA AI-ETC is an agentic platform for MARA entrepreneurship officers —
agents extract/analyze/draft, humans approve at defined gates, everything is
audited. You are not building the product; you are building the ground it
runs on. Read in this order:

1. [`docs/architecture/13-deployment-architecture.md`](../docs/architecture/13-deployment-architecture.md)
   — your actual spec: environments (dev/testing/staging/production),
   HA/DR targets, container strategy, Kubernetes readiness, cloud-agnostic
   Terraform structure. Every infra decision traces back to this document.
2. [`docs/architecture/11-security-architecture.md`](../docs/architecture/11-security-architecture.md)
   — network policy matters especially: the Market Agent (later milestone)
   is the *only* component ever allowed outbound internet egress, enforced
   at the network-policy level, not just application permissions. Tool
   Runtime sandboxes need their own tightly-policed namespace, distinct from
   Gateway/API services (§13.7). Don't design network topology that makes
   this harder to enforce later.
3. [`docs/repo-audit/06-openhands-protection-rules.md`](../docs/repo-audit/06-openhands-protection-rules.md)
   — why MARA additions are *additive*, layered compose/config files
   alongside OpenHands' own, never edits to OpenHands' own infra files.
   This is what keeps `git merge upstream/main` working.
4. [`infrastructure/compose/README.md`](compose/README.md) — the current
   dev-stack scaffold and its known state (below).

## Current state (update your understanding — this changes over time)

- ✅ Written: `infrastructure/compose/docker-compose.mara.yml`
  (postgres-primary + pgvector, postgres-dify as a genuinely separate
  instance, redis, minio, keycloak with realm auto-import) and
  `docker-compose.observability.yml` (otel-collector, prometheus, loki,
  grafana, langfuse).
- ❌ **Never run against a real Docker daemon.** No Docker was available in
  the environment that wrote these files. This is the single biggest gap —
  see "Immediate task" below.
- ❌ `infrastructure/docker/`, `infrastructure/k8s/`, `infrastructure/terraform/`
  — README stubs only, nothing implemented.
- The backend (`agents/`, `tools/`, `workflows/`, `services/`) has real,
  tested code as of Milestone 1, but it has only ever been tested against
  `langgraph`'s in-memory checkpointer (`InMemorySaver`) — **never against
  the real `postgres-primary` checkpointer path.** Standing up the stack for
  real is also what first proves that actually works.
- **New since the last update:** `services/api_gateway` now exposes two real
  HTTP endpoints (`POST /documents/assessments`,
  `POST /documents/assessments/{thread_id}/decision`) and
  `services/audit_service` writes approval decisions to the `audit_memory`
  table (already defined in `infrastructure/compose/init/postgres-primary-init.sql`
  since Milestone 0). Both are tested only against mocks/`InMemorySaver` —
  see item 7 below, this is now part of your immediate verification pass,
  not a separate task.

## Immediate task: stand up and verify the Docker stack

This is Milestone 0's last open item
([`docs/architecture/14-roadmap.md`](../docs/architecture/14-roadmap.md)
§14.2's acceptance criterion). Concretely:

```bash
docker compose \
  -f docker-compose.yml \
  -f infrastructure/compose/docker-compose.mara.yml \
  -f infrastructure/compose/docker-compose.observability.yml \
  up -d
```

Then verify, don't assume:
1. `docker compose ... config --quiet` passes (this is also what
   `mara-ci.yml`'s `compose-config` job checks on every PR — if it's been
   silently broken, fix the compose files here).
2. Every container reaches a healthy state — not just "started."
3. `postgres-primary` and `postgres-dify` are genuinely separate instances
   (ACCB Condition C-5) — connect to both independently and confirm.
4. Keycloak comes up, the realm imports from
   `infrastructure/compose/init/keycloak-realm-mara-ai-etc.json` without
   error, and a test login succeeds.
5. Run `services/api_gateway`'s `/diagnostics/synthetic-trace` endpoint (see
   `services/api_gateway/README.md` for the exact steps) and confirm the
   resulting trace is actually visible in Grafana (port 3000) — not just
   that the endpoint returned 200.
6. Run the real `tests/unit/mara` suite's checkpointer/workflow tests
   against `postgres-primary` instead of `InMemorySaver`, if practical —
   this is the first real chance to prove Postgres-backed checkpoint
   resumption works outside a mock. Flag it clearly if you don't get to
   this rather than silently skipping it.
7. **Verify real Audit Memory writes.** This is new, not in an earlier
   version of this file. **You cannot do this through the full HTTP flow
   yet** — `POST /documents/assessments` will always fail with a 503 before
   the workflow ever reaches its paused state, because no OCR engine or
   document classifier is wired (`tools/ocr/README.md`,
   `tools/documents/README.md`), so there's no valid `thread_id` to submit a
   decision against. Don't chase that as a bug; it's expected, current
   platform state. Instead, verify the write path directly and in
   isolation:
   ```python
   import asyncio
   from services.audit_service import AuditEvent, audit_pool, write_audit_event
   from shared.config import get_settings

   async def main():
       async with audit_pool(get_settings()) as pool:
           await write_audit_event(pool, AuditEvent(
               workflow_id='infra-verification-test',
               actor_id='dev-3',
               actor_role='officer',
               event_type='approval',
               payload={'note': 'manual verification'},
           ))
           rows = await pool.fetch(
               "SELECT * FROM audit_memory WHERE workflow_id = 'infra-verification-test'"
           )
           print(rows)

   asyncio.run(main())
   ```
   Confirm the row lands with the correct columns, and that `occurred_at`
   was set by the database (not the client). This has **never been run
   against a real database** — every test so far (`tests/unit/mara/test_audit_service.py`)
   mocks the `asyncpg` pool entirely.

**Report exactly what you verified vs. what you assumed.** A prior session
on this project got burned repeatedly by "done" claims that turned out to
be unrun or unverified — every status you report here should be something
you personally watched pass, not something that "should work."

## Conventions already established — follow, don't reinvent

- MARA's compose files are **additive**, layered on top of the root
  `docker-compose.yml` via `-f` flags — never merged into or replacing it.
- Dev-only secrets in compose/config files are intentionally obvious
  placeholders (`REPLACE_ME_DEV_ONLY`, `admin-dev-only`) — never let a real
  secret land in a committed file, and don't "clean up" a placeholder by
  making it look more production-real.
- Two Postgres instances, always — primary (platform state: memory, audit,
  checkpoints) and Dify's own (knowledge base). Never collapse these into
  one instance or one schema, even for convenience (ACCB Condition C-5 is a
  closed governance condition — reopening it needs a governance decision,
  not an infra shortcut).

## Before you finish any task

- State plainly what you ran, what passed, and what you couldn't verify —
  match the standard in "Immediate task" above.
- Don't touch `pyproject.toml`, `uv.lock`, or any file under `tests/unit/mara/`
  — if you find a backend bug while verifying infra, describe it and stop,
  don't fix it yourself.
- Don't touch `apps/officer-workspace/` — if the frontend needs an infra
  change (a new env var, a new exposed port), flag it rather than editing
  frontend files directly.
