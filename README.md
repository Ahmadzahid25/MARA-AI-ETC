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

**Currently on: Milestone 0 — Foundation** (of 7 milestones, `docs/architecture/14-roadmap.md` §14.2–§14.8). This is the single place to check "where are we" — update this block, not just the docs, whenever milestone status changes.

| Milestone 0 item | Status |
|---|---|
| ACCB Conditions C-1, C-2, C-3, C-5 | ✅ Closed |
| ACCB Condition C-4 (legal sign-off on OpenHands license) | ⏳ Open — not engineering's to close |
| Repo structure, Gateway, LangGraph checkpointer, model-tiering, compose files, CI | ✅ Built and code-verified (lint + real tests passing) |
| Unit tests for checkpointer, synthetic_trace, auth, gateway app, middleware | ✅ **Actually executed and passing**: `uv run pytest tests/unit/mara` — 50/50 passed. `ruff check`/`format` clean (now includes `tests/unit/mara` in `mara-ci.yml`'s lint job, which previously omitted it). Getting here required fixing a real `opentelemetry-sdk==1.39.1` / `opentelemetry-instrumentation-fastapi>=0.60` version conflict (the fastapi-instrumentation floor excluded the compatible `0.60b1` prerelease under PEP 440 ordering — fixed to `>=0.60b0,<1.0`) plus several real bugs the first successful run surfaced: a `_JwksCache` TTL off-by-one (`>` vs `>=`), a missing `ValueError` catch in `get_current_principal` for unrecognized JWT `kid`s (was an unhandled 500, not the documented 401), an authlib `as_dict()` call missing `is_private=True` (silently exported public-only keys), and a LangGraph checkpointer test mocked with a raw `AsyncMock` that didn't satisfy the real checkpointer protocol (replaced with `InMemorySaver`) |
| `apps/officer-workspace/` scaffolded (React SPA with Keycloak SSO login, empty workspace) | ✅ `npm install`, `tsc --noEmit`, and `npm run build` all pass (cache redirected off the machine's full `D:` drive). Fixed a broken TS project reference (`packages/openhands-ui` isn't a composite project) that made `build`/`typecheck` fail outright |
| Actually deployed / running (Docker stack up, Keycloak SSO login, trace visible in Grafana) | ❌ **BLOCKED** — no Docker available in this environment. Compose files exist but have never been run against a real Docker daemon. Must be verified on a machine with Docker before Milestone 0 counts as complete |
| Milestone 1 (Document Agent) | Not started |

Full detail: [`docs/architecture/14-roadmap.md`](docs/architecture/14-roadmap.md) (roadmap + acceptance criteria) and [`docs/governance/architecture-approval-report.md`](docs/governance/architecture-approval-report.md) (ACCB gate conditions, kept current).

**Everything above is local-only** — this repository has not been pushed to any remote (no `origin` configured). All work exists as commits on `git log` in this checkout.
