« [Index](00-INDEX.md) | Phase 3 of 16 »

# Phase 3 — Repository Structure

> **v1.0 note:** this phase was revised after the [repository audit](../repo-audit/00-index.md) inventoried the actual repository and after the [ACCB gate](../governance/architecture-approval-report.md) closed Conditions C-1 and C-2 against it. The structure below is now authoritative and matches [repo-audit/03-target-structure.md](../repo-audit/03-target-structure.md) exactly — that document carries the full folder-by-folder rationale; this phase carries the summary and the dependency rules.

## 3.1 Approach

This stays a **single monorepo built on the existing OpenHands checkout**, not a greenfield multi-repo split — and, per the repository audit, not a wholesale reorganization of OpenHands' own directories either. `openhands/`, `frontend/`, `containers/`, `kind/`, `tests/`, `scripts/`, and the root build/CI files stay exactly where they are. Moving them into a generic `apps/`/`core/` nesting (a natural first instinct for a "clean monorepo") was considered and explicitly rejected: it would break every existing path reference in the Makefile, CI workflows, and Dockerfiles, and — far more importantly — turn every future upstream OpenHands merge into a manual conflict-resolution exercise instead of a normal `git merge`. See [repo-audit/06-openhands-protection-rules.md](../repo-audit/06-openhands-protection-rules.md) for the full protection rules and upgrade strategy this implies.

`enterprise/` (OpenHands' own commercial SaaS surface — billing, hosted multi-tenant auth) is **not** part of this platform and is scheduled for removal (ACCB Condition C-3) — it is not listed in the tree below.

```
MARA AI-ETC/
├── openhands/                   # [existing, extended via library boundary — not edited in place]
│   └── app_server/              # event stream, sandbox, mcp, secrets, user_auth, git — the integration
│                                 # target ("V1"); openhands/server/ (legacy "V0") is read-only reference
├── frontend/                    # [existing] kept as the source packages/event-stream-client is extracted
│                                 # from; NOT reskinned into the officer product
├── containers/, kind/,          # [existing, unchanged location] OpenHands' own deployment definitions —
│   docker-compose.yml           # infrastructure/ below is additive alongside these, not a replacement
├── tests/, scripts/             # [existing, extended in place — new MARA test/script categories are
│                                 # added as siblings inside these, not a parallel tree]
│
├── apps/                        # [new] deployable end-user applications
│   └── officer-workspace/       # purpose-built MARA officer frontend (Phase 2 "Workspace" layer),
│                                 # consuming packages/event-stream-client and packages/openhands-ui
│
├── packages/                    # [new] shared, independently-versionable libraries
│   ├── openhands-ui/            # moved from repo root — reused design-system/component base, not rebuilt
│   └── event-stream-client/     # extracted from frontend/src's WebSocket/event-stream logic — the one
│                                 # part of the existing frontend genuinely worth reusing
│
├── agents/                      # [new] the 7 true MARA agents only — see Phase 5 §5.14 for the test
│   ├── planner/                 # applied to decide agent vs. service. Supervisor, Report, Presentation,
│   ├── document_agent/          # Voice, and Audit do NOT live here — they're in services/ below.
│   ├── compliance_agent/
│   ├── finance_agent/
│   ├── risk_agent/
│   ├── market_agent/
│   ├── recommendation_agent/
│   └── shared/                  # common agent base class, prompt templates, confidence scoring
│
├── tools/                       # MARA tool implementations (Phase 6), registered into the OpenHands
│   ├── ocr/                     # tool runtime / MCP host at openhands/app_server/mcp
│   ├── documents/                # word/excel/pptx generation & parsing
│   ├── audio/                    # TTS/STT primitives — consumed by services/voice_service, not an agent
│   ├── search/                   # web/enterprise search — includes the mandatory query-sanitization
│                                  # enforcement for the Market Agent's external search calls (Phase 6, 11)
│   ├── rag/                      # knowledge base query client (calls services/knowledge_service)
│   ├── database/                 # structured data query tools
│   ├── email/
│   ├── calculations/             # deterministic finance/risk formulas — never LLM-computed
│   └── mcp_servers/              # standalone MCP servers for tools best isolated as separate processes
│
├── services/                    # standalone backend services (own deploy unit, own DB schema/boundary)
│   ├── planner_service/         # Planner API surface
│   ├── supervisor_service/      # Supervisor's deterministic control logic (dispatch/retry/budget/escalate)
│   │                             # — implemented as LangGraph control flow, explicitly NOT an LLM agent
│   ├── publishing_service/      # merged Report + Presentation rendering — deterministic templating from
│   │                             # already-approved content, not agentic reasoning (Phase 5 §5.14)
│   ├── voice_service/           # TTS/STT tool wrapping — not an agent (Phase 5 §5.14)
│   ├── audit_service/           # structured, append-only audit query API; a thin narrative-generation
│   │                             # agent layer sits on top only for the specific "readable summary" use case
│   ├── memory_service/          # Memory read/write API (Phase 8)
│   ├── knowledge_service/       # Dify-backed RAG service, on its own separate database instance from the
│   │                             # platform's primary Postgres (Phase 9 — ACCB Condition C-5)
│   ├── approval_service/        # Human-in-the-loop gate management (Phase 10)
│   └── notification_service/    # Email/in-app notification dispatch
│
├── workflows/                   # LangGraph workflow graph definitions (Phase 7) — bounded, versioned
│   ├── document_assessment/     # templates that the Planner selects and parameterizes. Free runtime
│   ├── loan_assessment/         # construction of novel graph topology is explicitly out of scope — see
│   ├── market_research/         # Phase 7 §7.1 and Phase 5 §5.2.
│   ├── committee_report/
│   ├── risk_analysis/
│   ├── presentation_generation/
│   ├── audio_briefing/
│   └── human_review/
│
├── shared/                      # cross-cutting code shared by agents/tools/services/workflows
│   ├── schemas/                 # Pydantic/JSON-schema contracts (agent I/O, tool I/O, events)
│   ├── auth/                    # RBAC/ABAC policy evaluation, shared with app_server/user_auth
│   ├── telemetry/                # OpenTelemetry instrumentation helpers
│   ├── llm/                      # LLM provider abstraction (wraps OpenHands' existing litellm usage),
│   │                              # including the model-tiering routing rule (Phase 4 §4.6)
│   └── config/                   # typed config loading, environment resolution
│
├── infrastructure/              # deployment definitions (Phase 13) — additive alongside containers/, kind/
│   ├── docker/
│   ├── k8s/
│   ├── terraform/
│   └── compose/                 # local-dev overlays composed with the root docker-compose.yml
│
├── docs/                        # [existing — canonical, per ACCB Condition C-1; NOT "documentation/"]
│   ├── architecture/            # this document set
│   ├── repo-audit/              # repository audit and restructuring plan
│   ├── governance/              # ACCB approval reports and future gate decisions
│   ├── security/                # threat models, red-team records, third-party assessment reports
│   ├── deployment/              # deployment guides and operational runbooks
│   ├── api/                     # generated API reference
│   └── policy/                  # PDPA / compliance documentation
│
├── configs/                     # environment-specific, non-secret configuration
│   ├── dev/
│   ├── staging/
│   └── production/
│
└── tests/                       # [existing, extended] agent_evals/, integration/, e2e/ added as new
                                  # subfolders alongside the existing unit/ structure
```

## 3.2 Folder purpose reference

| Folder | Purpose | Owner (team) |
|---|---|---|
| `openhands/` | Extracted runtime substrate: event stream, sandboxed tool execution, MCP host, secrets, user auth, git integration | Platform |
| `apps/officer-workspace/` | Purpose-built officer workspace UI (chat, review console, dashboard, admin) | Frontend |
| `packages/` | Reused/extracted shared frontend libraries (`openhands-ui`, `event-stream-client`) | Frontend |
| `agents/` | Prompt/config/policy definitions for the 7 true agents only — no tool implementation lives here | Agents |
| `tools/` | Tool implementations: input/output contracts, permission declarations, error handling | Tools |
| `services/` | Independently deployable backend services, including the 5 reclassified components | Platform |
| `workflows/` | Bounded LangGraph graph templates wiring agents + tools + approval gates into business processes | Workflows |
| `shared/` | Contracts and cross-cutting infrastructure code imported by everything else — no business logic | Platform |
| `infrastructure/` | Everything needed to deploy the system to any environment, additive alongside OpenHands' own `containers/`/`kind/` | DevOps |
| `docs/` | All docs — architecture, repo audit, governance, security, deployment, API reference, policy | All teams |
| `configs/` | Non-secret environment configuration, loaded by `shared/config` | DevOps |
| `tests/` | Cross-cutting test suites; module-local unit tests stay next to their code, existing `tests/unit/` structure extended in place | QA/All teams |
| `scripts/` | One-off and recurring operational scripts, existing directory extended in place | DevOps |

## 3.3 Dependency rules

To keep the module graph acyclic and independently testable:

- `agents/` may depend on `shared/`, `tools/` (via typed client interfaces only, never direct imports of tool internals), and `services/*` clients.
- `tools/` may depend on `shared/` and `openhands/app_server/*` (sandbox, mcp). Tools must **not** import from `agents/` — a tool has no knowledge of which agent is calling it.
- `workflows/` may depend on `agents/`, `services/`, and `shared/`. Workflows are the only place that knows the full shape of a business process, and every workflow's shape is a bounded template (3.1), not runtime-constructed.
- `services/` may depend on `shared/` and `openhands/`. Services must **not** import from `agents/` or `workflows/` — services are lower-level than orchestration.
- `apps/officer-workspace/` may depend on `packages/*` and the API Gateway's published contract only — never directly on `agents/`, `services/`, or `openhands/` internals.
- `shared/` depends on nothing else in the repo (leaf dependency). This is enforced in CI via an import-linter/dependency-graph check, not just convention.

## 3.4 Why not microservices-from-day-one, and why not a monolith either

A pure microservices split (one repo/deploy per agent) is rejected for now: even at 7 agents plus a dozen tools, separate repos multiplies CI, versioning, and cross-service contract-testing overhead well beyond what a team at this stage can sustain, and the agents are being iterated on together (shared prompt patterns, shared evaluation harness) — repo-per-agent would slow that iteration down, not speed it up.

A pure monolith is also rejected: `services/` are deliberately separated by deploy boundary because they have different scaling and failure profiles — the Knowledge Service (CPU/embedding-heavy, can be scaled independently, and now runs on its own database instance per ACCB Condition C-5) and the Approval Service (low-throughput, must be highly available since a stuck approval blocks a workflow indefinitely) should not share a failure domain or a scaling policy.

The chosen shape — monorepo, service-boundary-by-folder, existing OpenHands directories left untouched — gives independent deployability where it matters (`services/`) while keeping agent/tool/workflow iteration in one coherent, atomically-committable codebase, and keeps the door open to a clean `git merge upstream/main` at any time. Splitting `services/*` into separate repos later, once boundaries have proven stable, is a low-cost follow-up; merging a prematurely-split microservice mesh back together — or unwinding a reorganization that broke upstream compatibility — is not.
