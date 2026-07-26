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

- **New since the last update (Milestone 2, backend side):** the RAG tool
  (`tools/rag/`) and the Knowledge Service *contract*
  (`services/knowledge_service/contract.py`) are implemented and tested against
  stub backends. **Dify itself is not deployed, and that is your work** — see
  "Coming next" below. Nothing in the backend blocks on it; the contract was
  defined first precisely so these two tracks run in parallel.

## Coming next: Dify, on its own database instance

This lands in Milestone 2 ([`14-roadmap.md`](../docs/architecture/14-roadmap.md)
§14.4) and it is your side of it. Read
[`09-knowledge-architecture.md`](../docs/architecture/09-knowledge-architecture.md)
§9.1.1 before starting.

**The non-negotiable part: Dify runs against `postgres-dify`, never
`postgres-primary`.** This is ACCB Condition C-5, not a preference. The reason
is concrete rather than stylistic — running a vendored service you do not intend
to schema-migrate in lockstep with your own application against a shared
database is the normal way an upgrade of one silently endangers the other. You
already have `postgres-dify` as a separate instance in
`docker-compose.mara.yml`; keep it that way, and resist any Dify quickstart that
points it at the main database.

Downstream consequences that are yours to carry, per §9.1.1:

- **Two databases, two backup schedules, two restore procedures**, tracked as
  such in the DR story ([`13-deployment-architecture.md`](../docs/architecture/13-deployment-architecture.md)).
  A DR drill that only restores `postgres-primary` has not been rehearsed.
- The platform's own pgvector index (for corpora outside Dify's direct
  management, §9.7's precedent-decision store) stays on `postgres-primary` and
  must stay clearly labelled as separate from whatever Dify considers
  authoritative for its own state.

**What the backend needs from you, concretely:** a reachable Dify instance plus
the connection/credential config, so someone can implement
`KnowledgeBackend.retrieve()` against it. The interface is one async method —
see `services/knowledge_service/contract.py`. You are not implementing the
adapter (that is backend work, in `services/`), you are making Dify exist and be
reachable.

**One behavior to preserve when you wire config:** an unconfigured backend must
raise, not return empty results. `services/knowledge_service` already does this
deliberately — "the corpus was searched and had nothing" and "no corpus was
reached" must stay distinguishable, or a misconfigured deployment produces
confident "no applicable policy found" compliance findings against a corpus it
never touched. If you add a config path that silently degrades to an empty
corpus, you have removed that guarantee.

**Egress posture is unchanged by this.** Dify is an internal service; it does
not get outbound internet access. The sole external-egress path in this platform
remains the Market Agent's search tool
([`11-security-architecture.md`](../docs/architecture/11-security-architecture.md)
§11.7), and that is enforced by network policy, not convention — a second egress
path acquired incidentally while wiring a new service is exactly what §11.7
exists to prevent.

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

8. **New table needed: `long_term_memory_calibration`.** Not yet in
   `infrastructure/compose/init/postgres-primary-init.sql` — this is a
   request from the backend/AI-agent side, not something you need to design,
   just apply. `services/memory_service/calibration.py` (new) writes to it;
   ACCB governance requires this loop "actually built and actively
   monitored from Milestone 1 onward, not treated as a nice-to-have"
   ([architecture-approval-report.md](../docs/governance/architecture-approval-report.md)
   §5). Add this DDL to `postgres-primary-init.sql`, matching the existing
   `audit_memory` table's style (append-only, indexed, no update/delete
   path):
   ```sql
   -- Long-term Memory: confidence-calibration tracking (docs/architecture/
   -- 08-memory-architecture.md §8.2). One row per extracted field per
   -- workflow, recording the agent's stated confidence and whether an
   -- officer subsequently corrected it — the raw signal a periodic batch
   -- job aggregates into calibration reports. Append-only, like
   -- audit_memory, so calibration drift is analyzable over time rather
   -- than overwritten.
   CREATE TABLE IF NOT EXISTS long_term_memory_calibration (
       id                 BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
       recorded_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
       agent_name         TEXT NOT NULL,
       workflow_id        UUID,
       field_name         TEXT NOT NULL,
       document_type      TEXT,
       stated_confidence  DOUBLE PRECISION NOT NULL,
       was_corrected      BOOLEAN NOT NULL
   );

   CREATE INDEX IF NOT EXISTS idx_calibration_agent_field
       ON long_term_memory_calibration (agent_name, field_name);
   CREATE INDEX IF NOT EXISTS idx_calibration_workflow_id
       ON long_term_memory_calibration (workflow_id);
   ```
   Once applied, verify the same way as item 7 — a direct isolated script
   using `services.memory_service.calibration.write_calibration_event`, not
   the full HTTP flow (same OCR-engine blocker applies).

9. **New trust boundary needed: Market Agent network egress policy.**
   `agents/market_agent/market_agent.py` and `tools/search/search_tool.py`
   (new, Milestone 3, backend side) now exist for real — the platform's one
   component with an actual outbound-search code path. Per
   [`06-tool-architecture.md` §6.6](../docs/architecture/06-tool-architecture.md#66-query-sanitization-on-the-webexternal-search-tool-added-in-v10--accb-mandatory-change-1)
   (ACCB Mandatory Change 1), both controls — query sanitization
   (application-level) and network-policy-level egress enforcement
   (infrastructure-level) — are launch preconditions for the Market Agent,
   not a follow-on hardening pass. Query sanitization is implemented and
   tested (`tools/search/query_sanitizer.py`); this network-policy half is
   still open and is your side of it, same division of labor as the Dify
   adapter above. Needs, once `infrastructure/k8s/` has real manifests
   (currently a README stub): a `NetworkPolicy` scoped to the Market
   Agent's pod selector denying all egress except DNS + the search
   provider's allow-listed destinations — coordinate that allow-list with
   `tools/search/search_tool.py`'s `allowed_domains` parameter (currently
   caller-supplied at call time, not yet exposed as shared config; flag
   back to the backend side if it should be). Every other agent/service
   pod's egress stays cluster-internal-only, per the "Egress posture"
   section above.

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
