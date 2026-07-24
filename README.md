# MARA AI-ETC

**MARA AI Entrepreneurship Transformation Centre**
*From Documents to Decisions, From Insights to Impact.*

An Agentic AI platform for MARA (Majlis Amanah Rakyat) entrepreneurship officers: it plans work, executes it through tools, gathers evidence, drafts outputs, and waits for human approval — with a complete audit trail. It is not a chatbot, and it does not make loan or grant decisions; human officers always do.

## Start here

The full engineering plan lives in [`docs/architecture/00-INDEX.md`](docs/architecture/00-INDEX.md) — **Architecture Baseline v1.0**, the current, approved source of truth. Read that before writing any code against this repository.

| Document set | Purpose |
|---|---|
| [`docs/architecture/`](docs/architecture/00-INDEX.md) | The 16-phase master architecture plan (vision, system design, agents, tools, workflows, security, roadmap, etc.) |
| [`docs/architecture/review/`](docs/architecture/review/00-review-index.md) | Independent Architecture Review Board critique (point-in-time record — findings already merged into the baseline) |
| [`docs/repo-audit/`](docs/repo-audit/00-index.md) | Repository inventory and restructuring plan this codebase follows |
| [`docs/governance/`](docs/governance/architecture-approval-report.md) | Formal Architecture Change Control Board (ACCB) approval decisions and gate conditions |

## Relationship to OpenHands

This repository is built on top of an [OpenHands](https://github.com/OpenHands) checkout (specifically, OpenHands Agent Canvas). That is a deliberate architecture decision, not incidental: MARA AI-ETC extracts and builds against specific OpenHands subsystems (`openhands/app_server/*` — event stream, sandboxed tool execution, MCP host, secrets, user auth) as its Agent and Tool Runtime substrate, rather than rebuilding solved infrastructure. See [`docs/architecture/04-technology-stack.md`](docs/architecture/04-technology-stack.md) for the full justification and the [OpenHands protection rules](docs/repo-audit/06-openhands-protection-rules.md) governing what may and may not be modified in the upstream-derived parts of this tree.

The original OpenHands/Agent Canvas project documentation, community links, and contribution process are preserved for reference in [`docs/upstream-reference/`](docs/upstream-reference/) — they describe the upstream open-source project, not MARA AI-ETC's own process (see [`CONTRIBUTING.md`](CONTRIBUTING.md) for this repository's own contribution guidelines).

## Repository layout

```
agents/       MARA domain agents (Document, Compliance, Finance, Risk, Market, Recommendation, Planner)
tools/        Tool implementations (OCR, documents, search, RAG, database, calculations, ...)
services/     Backend services, including the reclassified Supervisor/Publishing/Voice/Audit components
workflows/    Bounded LangGraph workflow templates
shared/       Cross-cutting contracts and infrastructure code
apps/         End-user applications (officer-workspace)
packages/     Shared, independently-versionable libraries
infrastructure/  Deployment definitions (Docker, Kubernetes, Terraform, compose)
configs/      Environment-specific configuration
openhands/    Extracted OpenHands runtime substrate (protected — see docs/repo-audit/06-openhands-protection-rules.md)
frontend/     OpenHands' own dev-console UI (kept as extraction source, not the officer product)
```

Full rationale in [`docs/architecture/03-repository-structure.md`](docs/architecture/03-repository-structure.md).

## Status

**Currently on: Milestone 1 — Document Agent** (of 7 milestones, `docs/architecture/14-roadmap.md` §14.2–§14.8). This is the single place to check "where are we" — update this block, not just the docs, whenever milestone status changes.

### Milestone 0 — Foundation

| Milestone 0 item | Status |
|---|---|
| ACCB Conditions C-1, C-2, C-3, C-5 | ✅ Closed |
| ACCB Condition C-4 (legal sign-off on OpenHands license) | ⏳ Open — not engineering's to close |
| Repo structure, Gateway, LangGraph checkpointer, model-tiering, compose files, CI | ✅ Built and code-verified (lint + real tests passing) |
| Unit tests for checkpointer, synthetic_trace, auth, gateway app, middleware | ✅ **Actually executed and passing**: `uv run pytest tests/unit/mara` — 50/50 passed. `ruff check`/`format` clean (now includes `tests/unit/mara` in `mara-ci.yml`'s lint job, which previously omitted it). Getting here required fixing a real `opentelemetry-sdk==1.39.1` / `opentelemetry-instrumentation-fastapi>=0.60` version conflict (the fastapi-instrumentation floor excluded the compatible `0.60b1` prerelease under PEP 440 ordering — fixed to `>=0.60b0,<1.0`) plus several real bugs the first successful run surfaced: a `_JwksCache` TTL off-by-one (`>` vs `>=`), a missing `ValueError` catch in `get_current_principal` for unrecognized JWT `kid`s (was an unhandled 500, not the documented 401), an authlib `as_dict()` call missing `is_private=True` (silently exported public-only keys), and a LangGraph checkpointer test mocked with a raw `AsyncMock` that didn't satisfy the real checkpointer protocol (replaced with `InMemorySaver`) |
| `apps/officer-workspace/` scaffolded (React SPA with Keycloak SSO login, empty workspace) | ✅ `npm install`, `tsc --noEmit`, and `npm run build` all pass (cache redirected off the machine's full `D:` drive). Fixed a broken TS project reference (`packages/openhands-ui` isn't a composite project) that made `build`/`typecheck` fail outright |
| Actually deployed / running (Docker stack up, Keycloak SSO login, trace visible in Grafana) | ❌ **BLOCKED** — no Docker available in this environment. Compose files exist but have never been run against a real Docker daemon. Must be verified on a machine with Docker before Milestone 0 counts as complete |

### Milestone 1 — Document Agent (in progress)

`workflows/document_assessment/` scope decision (approved): Compliance Agent
is pulled into this workflow now, per `07-workflow-architecture.md` §7.3's
"Document → Compliance" catalogue entry — but its policy-matching logic
stays an honest stub until `services/knowledge_service` exists (Milestone 2,
per `14-roadmap.md` §14.4). See `agents/compliance_agent/README.md`.

| Milestone 1 item | Status |
|---|---|
| `shared/schemas/` — document extraction, compliance, and approval contracts (`DocumentExtractionRecord`, `ComplianceChecklist`, `ApprovalDecisionInput`, ...) | ✅ Built and tested. Shared contract `apps/officer-workspace/` (frontend) and the backend agents/services both consume — see `apps/officer-workspace/AGENTS.md` |
| `shared/schemas/` — tool error taxonomy + audit-log stub (`ToolError` family, `ToolInvocationLog`, `log_tool_invocation`) | ✅ Built and tested. Audit sink defaults to structured logging, not a real Audit Memory write — `services/audit_service` doesn't exist yet (tracked with a `TODO(milestone-1)`, reused identically by `services/approval_service`) |
| `tools/ocr/` — OCR tool (`run_ocr`) | ✅ Timeout/retry/permission/audit-log behavior built and tested against injected fake engines. **No real OCR engine wired** — self-hosted PaddleOCR/Tesseract integration is a separate follow-up task; the default engine raises a clear typed error rather than fabricating results |
| `tools/documents/` — PDF parse (`parse_pdf`) + document classification (`classify_document`) | ✅ Built and tested against **real `pypdf`-generated PDFs**, not mocks. Native text-layer extraction is real; OCR fallback works when a page-image renderer is injected (none wired by default). Table extraction not implemented — no table-detection library chosen yet. No real document-classifier model wired |
| `agents/document_agent/` — `DocumentAgent.process_document()` | ✅ Built and tested. Classifies + parses via the tools above, then an LLM call (via `TieredLLMClient`, Document tier) turns raw page text into named, confidence-scored fields. **Not wired into the OpenHands event-stream Agent Runtime** — that integration is a separate, larger task; this agent is directly callable in the meantime |
| `agents/compliance_agent/` — `ComplianceAgent.check_compliance()` | ✅ Built and tested (Milestone-1 stub, scope decision above). Checklist structure and hard-violation detection are real; policy-matching always resolves to `NO_POLICY_FOUND` until Knowledge Service exists — §5.4's own specified behavior for "no corpus," not a fabricated shortcut |
| `workflows/document_assessment/` — `build_document_assessment_graph()` | ✅ Built and tested, including a **real** LangGraph `interrupt()`/`Command(resume=...)` durable pause at the "confirm extraction" gate (verified with `InMemorySaver`, not mocked) — Document Agent → Validation → confirm-extraction pause → Compliance Agent (on approval) → Completion. A rejected extraction currently routes to Completion without an automatic targeted re-run (named simplification, not silently dropped) |
| `services/approval_service/` — `confirm_extraction()` | ✅ Built and tested, including an **end-to-end integration test** resuming a real compiled workflow graph (not just a mocked one). All three actions (Approve/Reject/**Correct**) implemented per `10-human-in-the-loop.md` §10.5; a Correct action's field corrections verifiably reach the workflow's `extraction_record`, not just the audit log |
| `services/api_gateway` — `POST /documents/assessments` + `POST /documents/assessments/{thread_id}/decision` | ✅ Built and tested end-to-end (auth required, real `ToolError`→HTTP status mapping, real workflow pause/resume through the actual HTTP layer, not just the Python functions). This is the literal Milestone 1 deliverable ("an officer can upload a document...") — previously the agents/workflow existed but were unreachable outside Python. **Composition-root exception, flagged for review**: `services/api_gateway/composition.py` imports `agents/`/`workflows/` directly to construct the real graph, since `docs/architecture/03-repository-structure.md` §3.3 forbids `services/` from doing so and no `supervisor_service` exists yet to be the sanctioned mediator — isolated to that one file and documented there, everything else in `api_gateway` depends only on the `ResumableWorkflow` protocol |
| `services/audit_service` — `write_audit_event()` + `query_audit_events()` | ✅ Built and tested (mocked `asyncpg` pool — **never run against real Postgres**, no Docker in this environment). **Pulled forward from Milestone 5 by explicit decision.** Wired as the real writer for approval decisions via `confirm_extraction(audit_writer=...)`, all the way through `services/api_gateway`. Writes to the `audit_memory` table already defined since Milestone 0. Tool-call audit logging (`tools/ocr`, `tools/documents`) still uses the structured-logging stub — sync/async mismatch between those tools' sync calls and this service's `asyncpg`-only writes, flagged as a follow-up, not silently bridged |
| Test suite | ✅ 168/168 passing (`uv run pytest tests/unit/mara`), `ruff check`/`format` clean |

Full detail: [`docs/architecture/14-roadmap.md`](docs/architecture/14-roadmap.md) (roadmap + acceptance criteria) and [`docs/governance/architecture-approval-report.md`](docs/governance/architecture-approval-report.md) (ACCB gate conditions, kept current).

**Everything above is local-only** — this repository has not been pushed to any remote (no `origin` configured). All work exists as commits on `git log` in this checkout.
