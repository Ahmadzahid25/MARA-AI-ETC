# MARA AI-ETC — Architecture Baseline v1.0

**MARA AI Entrepreneurship Transformation Centre**
*From Documents to Decisions, From Insights to Impact.*

| | |
|---|---|
| **Status** | APPROVED WITH CONDITIONS ([ACCB gate](../governance/architecture-approval-report.md)) — conditions C-1, C-2, C-5 and Mandatory Changes 1–2 closed by this baseline; C-3, C-4 remain open (they require actions outside documentation — see [Baseline changelog](#baseline-v10-changelog) below) |
| **Version** | 1.0 |
| **Supersedes** | The original 16-phase draft plan as first written, and the standalone Architecture Review Board findings — both are now merged into the phase documents below. The review board report and repo audit remain as point-in-time records; this index is the current source of truth. |

This is the enterprise engineering plan for MARA AI-ETC: an Agentic AI Operating System for MARA officers, not a chatbot. It plans, delegates, executes tools, gathers evidence, reasons, drafts outputs, and waits for human approval — with a complete audit trail. No production code exists yet; this baseline is the blueprint every implementation PR must trace back to, and — per Condition C-2 of the ACCB gate — the corrections identified during review are now written into the phase documents themselves, not left in a separate critique a developer might not read.

This repository (`MARA AI-ETC/`) is itself an OpenHands checkout being evolved into MARA AI-ETC. Per the corrected [04-technology-stack.md](04-technology-stack.md) and the [repository audit](../repo-audit/00-index.md), that means **extracting and building against specific subsystems** (`openhands/app_server/*`: event stream, sandbox, MCP host, secrets, user auth) — not forking the entire tree. `frontend/` is kept in place as the source the reusable event-stream client is extracted from, not reskinned; `enterprise/` (OpenHands' own commercial SaaS surface) is not part of the platform at all and is scheduled for removal (Condition C-3).

## Reading order

| # | Document | Covers |
|---|----------|--------|
| 1 | [01-vision.md](01-vision.md) | Goals, non-goals, users, business value, success criteria, constraints |
| 2 | [02-system-architecture.md](02-system-architecture.md) | Full layered architecture, every component's responsibility |
| 3 | [03-repository-structure.md](03-repository-structure.md) | Production monorepo layout — aligned with the repository audit's target structure |
| 4 | [04-technology-stack.md](04-technology-stack.md) | Stack choices, alternatives, reuse/extract/inspire/replace verdicts, model-tiering |
| 5 | [05-agent-architecture.md](05-agent-architecture.md) | The 7 true agents (I/O, memory, tools, permissions, escalation) + 5 reclassified services |
| 6 | [06-tool-architecture.md](06-tool-architecture.md) | All tools: contracts, permissions, error handling, citation verification |
| 7 | [07-workflow-architecture.md](07-workflow-architecture.md) | End-to-end workflows as bounded LangGraph state-graph templates |
| 8 | [08-memory-architecture.md](08-memory-architecture.md) | Conversation/task/long-term/knowledge/shared/audit memory |
| 9 | [09-knowledge-architecture.md](09-knowledge-architecture.md) | Enterprise RAG: ingestion, chunking, citation, lifecycle, Dify database boundary |
| 10 | [10-human-in-the-loop.md](10-human-in-the-loop.md) | Approval gates, corrections, escalation, rollback |
| 11 | [11-security-architecture.md](11-security-architecture.md) | RBAC/ABAC, PDPA, prompt injection, data leakage, query sanitization, isolation |
| 12 | [12-observability.md](12-observability.md) | Logging, tracing, metrics, cost tracking, incident investigation |
| 13 | [13-deployment-architecture.md](13-deployment-architecture.md) | Environments, HA, DR, Kubernetes, backups |
| 14 | [14-roadmap.md](14-roadmap.md) | Milestones, dependencies, acceptance criteria, ACCB gate checkpoints |
| 15 | [15-risk-assessment.md](15-risk-assessment.md) | Technical/business/security/operational/AI/scaling risks |
| 16 | [16-future-expansion.md](16-future-expansion.md) | Voice-first, mobile, MCP servers, gov integrations |

## Non-negotiable principles

Every decision in this plan is judged against these, in this order, when they conflict:

1. **Human officers make the final decision.** The system recommends and drafts; it never autonomously commits MARA to a financial, legal, or reputational position.
2. **Every action is auditable.** If it isn't logged with who/what/why/when, it didn't happen, as far as compliance is concerned.
3. **Security and PDPA compliance are load-bearing, not bolted on.** Applicant financial and personal data drives this system; a breach or an unauthorized model call on sensitive data is an existential risk to the programme, not a bug.
4. **Reuse before building.** OpenHands, LangGraph, CrewAI, LibreChat, and Dify each solve a piece of this problem already — extracted and extended, never re-derived. See the reuse matrix below.
5. **Modularity over cleverness.** Agents, tools, and workflows are independently testable, independently deployable where practical, and loosely coupled through typed events — not through shared mutable state or implicit ordering.
6. **A component is only an agent if it makes a genuinely ambiguous judgment call.** Deterministic transformation or orchestration work is a service, never dressed up as an LLM-reasoning agent for uniformity's sake. (Added in v1.0 — see changelog.)

## Governance trail

This baseline is the fourth and current document in a chain — read in this order if you want the full reasoning history, or just read this index and the 16 phases if you want the current, authoritative state:

1. [Architecture Review Board report](review/00-review-index.md) — independent critique of the original draft plan; verdict "Approved with modifications." Findings now merged into the phases below (see changelog).
2. [Repository audit](../repo-audit/00-index.md) — inventory of the actual repository and target structure; findings now merged into [03-repository-structure.md](03-repository-structure.md).
3. [ACCB architecture approval report](../governance/architecture-approval-report.md) — formal gate decision, "Approved with Conditions," dated against the pre-v1.0 documents.
4. **This baseline (v1.0)** — the conditions closable through documentation are closed here. Two remain open and are tracked, not hidden: **C-3** (the `enterprise/` removal PR is a repository action, not a documentation change — see [repo-audit/04-migration-plan.md](../repo-audit/04-migration-plan.md) Phase 1–2) and **C-4** (MARA legal/procurement sign-off on upstream licensing is outside engineering's authority to close).

## Baseline v1.0 changelog

Every entry below is a merge of a previously-separate recommendation into its authoritative phase document — this is the concrete execution of ACCB Condition C-2 and the Mandatory Changes from [governance/architecture-approval-report.md](../governance/architecture-approval-report.md) §3–4.

| Change | Phase document(s) updated | Source finding |
|---|---|---|
| OpenHands verdict corrected from "fork the whole tree" to "extract and build against specific `app_server/*` subsystems" | [04-technology-stack.md](04-technology-stack.md), [03-repository-structure.md](03-repository-structure.md) | Review board Part 1 §2.5 |
| Planner constrained to bounded, versioned workflow-template selection/parameterization — free graph-topology construction explicitly forbidden | [05-agent-architecture.md](05-agent-architecture.md) §5.2, [07-workflow-architecture.md](07-workflow-architecture.md) | Review board Finding A1 |
| Deterministic citation verification added as a Tool Runtime enforcement step, not schema-presence checking alone | [06-tool-architecture.md](06-tool-architecture.md) | Review board Finding A2 |
| Supervisor, Report Agent, Presentation Agent, Voice Agent, and (mostly) Audit Agent reclassified from full LLM agents to services/control logic — 12 agents → 7 agents + 5 services | [05-agent-architecture.md](05-agent-architecture.md), [02-system-architecture.md](02-system-architecture.md), [03-repository-structure.md](03-repository-structure.md), [14-roadmap.md](14-roadmap.md) | Review board Part 2 |
| Market Agent search tool: query-sanitization enforcement (PII stripped/generalized before external egress) + network-policy-level egress restriction, both mandatory before this agent ships | [06-tool-architecture.md](06-tool-architecture.md), [11-security-architecture.md](11-security-architecture.md) | Review board Finding B3 / ACCB Mandatory Change 1 |
| Market-data caching into Knowledge Memory routed through the same document-lifecycle approval gate as other knowledge content (or explicitly segregated as a low-trust tier) | [09-knowledge-architecture.md](09-knowledge-architecture.md) §9.7 | Review board Finding C3 / ACCB Mandatory Change 2 |
| Dify's operational database declared an explicit, separate instance from the platform's primary Postgres | [09-knowledge-architecture.md](09-knowledge-architecture.md) | Review board Finding C2 / ACCB Condition C-5 |
| Model-tiering strategy specified explicitly per agent (Haiku-tier extraction, Sonnet-tier synthesis, Opus-tier reserved for Recommendation only) | [04-technology-stack.md](04-technology-stack.md) §4.6 | Review board Part 4 §10.2 |
| `docs/` taxonomy finalized as `{architecture/, repo-audit/, security/, deployment/, api/, policy/}`, replacing the original `documentation/{architecture, runbooks, api, policy}` | [03-repository-structure.md](03-repository-structure.md), [13-deployment-architecture.md](13-deployment-architecture.md), [11-security-architecture.md](11-security-architecture.md) | ACCB Condition C-1 |
| `apps/officer-workspace/` and `packages/` (including reused `openhands-ui/`) added to the repository structure as the frontend answer | [03-repository-structure.md](03-repository-structure.md), [04-technology-stack.md](04-technology-stack.md) | Repo audit §3.2, ACCB Decision 4 |

## Technology baseline verdicts (summary)

Full justification in [04-technology-stack.md](04-technology-stack.md); the short answer, since it governs every other phase:

| Baseline project | Verdict | Used for |
|---|---|---|
| **OpenHands** | Extract & build against specific subsystems (`app_server/event`, `sandbox`, `mcp`, `secrets`, `user_auth`) — not a whole-tree fork | Agent/Tool Runtime substrate, sandboxed tool execution, event stream, session/conversation persistence, MCP host, secrets vault, human-confirmation mode |
| **LangGraph** | Reuse directly | Workflow engine: bounded, versioned checkpointed state-graph templates, branching, retries, durable human-in-the-loop pauses |
| **CrewAI** | Inspiration only (concepts, not runtime) | Role/goal/backstory-style agent definition pattern, applied only to the 7 true agents, folded into LangGraph nodes rather than run as a second orchestrator |
| **LibreChat** | Inspiration only | Conversation list UX, multi-model picker, file-upload affordances — applied to the new purpose-built `apps/officer-workspace/`, not a fork of the OpenHands frontend's existing screens |
| **Dify** | Reuse directly, as an isolated internal service on its own database instance | Knowledge ingestion, chunking, dataset admin, RAG retrieval API — called by `services/knowledge_service`, not used as a second agent orchestrator |
