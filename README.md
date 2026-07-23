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
| Actually deployed / running (Docker stack up, Keycloak SSO login, trace visible in Grafana) | ❌ Not done — no Docker available in the environment that built this; needs to be run and verified before Milestone 0 counts as complete |
| Milestone 1 (Document Agent) | Not started |

Full detail: [`docs/architecture/14-roadmap.md`](docs/architecture/14-roadmap.md) (roadmap + acceptance criteria) and [`docs/governance/architecture-approval-report.md`](docs/governance/architecture-approval-report.md) (ACCB gate conditions, kept current).

**Everything above is local-only** — this repository has not been pushed to any remote (no `origin` configured). All work exists as commits on `git log` in this checkout.
