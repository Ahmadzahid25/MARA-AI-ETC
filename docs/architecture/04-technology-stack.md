« [Index](00-INDEX.md) | Phase 4 of 16 »

# Phase 4 — Technology Stack

Each recommendation states the verdict — **Reuse directly**, **Extract & customize**, **Inspiration only**, or **Replace with alternative** — per the mandated baseline (OpenHands, CrewAI, LangGraph, LibreChat, Dify), plus justification and the alternatives considered.

> **v1.0 note:** the OpenHands verdict below was corrected from "Fork & customize" (whole-tree fork) to "Extract & customize" (specific subsystems) per the Architecture Review Board's finding ([review/01-architecture-and-foundation-review.md](review/01-architecture-and-foundation-review.md) §2) and ACCB Condition C-2. The distinction matters: this repository remains an OpenHands checkout, but MARA code depends on `openhands/app_server/*` as a library boundary — it does not fork `frontend/`'s existing screens or `enterprise/` (removed entirely, ACCB Condition C-3).

## 4.1 Orchestration & agent runtime

### Workflow engine — **LangGraph — Reuse directly**
Alternatives considered: Temporal, plain Celery chains, a hand-rolled state machine.
- **Why LangGraph over Temporal:** Temporal gives stronger durability guarantees for arbitrary long-running business processes, but at the cost of a separate cluster to operate and a workflow-as-code model that doesn't natively understand LLM message state, tool-call loops, or streaming. LangGraph's `StateGraph` + Postgres checkpointer gives us exactly the durability we need (a workflow paused at a human-approval node for days survives restarts and resumes on any worker) while natively modeling the agent message/tool-call state we're checkpointing. Temporal remains a candidate if MARA later needs cross-system saga orchestration beyond AI workflows (see [16-future-expansion.md](16-future-expansion.md)).
- **Why not hand-rolled:** checkpointing, branching, and retry semantics are exactly the kind of solved infrastructure problem [00-INDEX.md](00-INDEX.md)'s reuse principle says not to rebuild.

### Agent definition pattern — **CrewAI — Inspiration only, not the runtime**
CrewAI's `Agent(role, goal, backstory, tools)` abstraction is a clean, well-tested mental model for defining a specialized agent, and we adopt that shape in `agents/*` (see [05-agent-architecture.md](05-agent-architecture.md)). But CrewAI's own `Crew`/`Process` orchestration loop is **not** used as the runtime: running it as a second orchestrator alongside LangGraph would mean two different systems both claim ownership of retries, state, and human-in-the-loop pauses — a coupling and audit-trail nightmare. Instead, each CrewAI-style agent definition is executed as a node inside a LangGraph graph, getting LangGraph's checkpointing "for free" without a second engine.

### Agent/tool execution substrate — **OpenHands — Extract & customize specific subsystems, not a whole-tree fork**
This repository is already an OpenHands checkout, but "we're inside the tree" and "we fork the whole tree" are different decisions, and the Architecture Review Board correctly separated them ([review/01-architecture-and-foundation-review.md](review/01-architecture-and-foundation-review.md) §2). OpenHands' sandbox is built to give a coding agent broad shell/code execution by default — the opposite of the narrow, per-agent, addition-based permission posture MARA needs (see [11-security-architecture.md](11-security-architecture.md)). Forking the entire `app_server` tree means inheriting that broad-capability default and stripping it down per agent (security-by-subtraction); extracting specific subsystems as a library boundary and layering MARA's addition-based permission model in front of them is the safer default and the one this baseline adopts. Concretely extracted, evidenced by the existing `openhands/app_server/*` tree:
- `app_server/event`, `event_callback` — the action/observation event stream becomes the Agent Runtime's execution loop (Layer 4 in [02-system-architecture.md](02-system-architecture.md)).
- `app_server/sandbox` — treated as an opaque execution primitive the Tool Runtime dispatches into (Layer 5) — MARA's permission model decides *whether* a call reaches it, never modifies *what it's capable of* (see [repo-audit/06-openhands-protection-rules.md](../repo-audit/06-openhands-protection-rules.md) §6.3).
- `app_server/mcp` — already an MCP host; this is the extension point for new tools (see [06-tool-architecture.md](06-tool-architecture.md)) instead of building a plugin system from scratch.
- `app_server/secrets` — secret storage/retrieval for tool credentials, integrated with the platform Secrets Manager (see [11-security-architecture.md](11-security-architecture.md)).
- `app_server/user_auth`, `app_server/git`, `app_server/app_conversation` — session/conversation persistence and identity plumbing, extended rather than replaced.
- What is explicitly **not** extracted or forked: `frontend/`'s existing coding-agent screens (see §4.2) and `enterprise/` (OpenHands' own commercial SaaS surface — billing, hosted multi-tenant auth — has no MARA function and is removed, per the [repository audit](../repo-audit/02-problems-found.md) P-01 and ACCB Condition C-3).
- Customization required: MARA's agents are narrowly scoped (no arbitrary shell/code execution for e.g. the Compliance Agent) — new MARA modules (`openhands/app_server/mara_*`) register into the existing extension points above rather than modifying `app_server` internals in place, keeping `git merge upstream/main` viable at all times (the concrete compatibility test in [repo-audit/06-openhands-protection-rules.md](../repo-audit/06-openhands-protection-rules.md) §6.4).

## 4.2 Frontend / workspace

### Chat workspace shell — **Extracted OpenHands event-stream client, new purpose-built application**
### Conversation UX patterns — **LibreChat — Inspiration only**
### Design system — **openhands-ui — Reuse directly**

Corrected in v1.0: the original draft proposed forking the OpenHands frontend wholesale. The Architecture Review Board rejected the *scope* of that ([review/01-architecture-and-foundation-review.md](review/01-architecture-and-foundation-review.md) §2.1): `frontend/` is built around a coding-agent UX (file tree, terminal, browser preview, single-conversation model) that shares almost no component surface with MARA's actual needs (a multi-workflow Review & Approval Console with document-and-citation evidence display, a portfolio Dashboard, a role-scoped Admin Console). Reskinning that UI is not cheaper than building fresh against the same backend.

What's approved instead, and now reflected in [03-repository-structure.md](03-repository-structure.md): **`packages/event-stream-client/`** is extracted from `frontend/src`'s actual WebSocket/event-stream handling — the one part of the existing frontend genuinely worth reusing — and **`apps/officer-workspace/`** is a new application built against it. `frontend/` itself is left in place, unmodified, as OpenHands' own dev-console UI and as the extraction source. LibreChat remains inspiration-only for conversation-list UX, multi-model picker, and file-upload affordances, applied to the new app. `openhands-ui/` (a standalone, Storybook-documented design-system package already present in this repository, moved to `packages/openhands-ui/`) is reused directly as the officer workspace's component base — this reuse opportunity was identified by the repository audit, not the original draft plan, and avoids building a design system from zero.

## 4.3 Knowledge / RAG

### Knowledge ingestion & retrieval — **Dify — Reuse directly, as an isolated internal service**
Alternatives considered: build a custom RAG pipeline on LlamaIndex/LangChain retrievers; use Dify's full application (including its own agent/app builder).
- Self-hosted Dify Community Edition is run as `services/knowledge_service`'s backing engine: its dataset ingestion, chunking pipeline, embedding management, and retrieval API are mature and directly reusable, saving months of building document-lifecycle and chunking-strategy tooling from scratch.
- We do **not** expose or use Dify's own chat/agent-builder UI or its orchestration engine — that would create a second, competing agent framework alongside LangGraph/OpenHands. Dify is scoped strictly to knowledge ingestion + retrieval, accessed by the Knowledge Agent and RAG tool via API, invisible to end users.
- This is a "reuse directly" rather than "fork" because we don't need to modify Dify's internals — we operate it as a bounded internal service behind our own API contract, which also means a future swap to a different RAG engine only touches `services/knowledge_service`, not every agent that queries it.

### Vector store — **PostgreSQL + pgvector — Reuse directly (start), Qdrant as scale-out path**
Alternatives: Qdrant, Weaviate, Milvus, Pinecone (managed/SaaS).
- Starting on pgvector keeps embeddings in the same transactionally-consistent, self-hostable, PDPA-auditable database as everything else in [08-memory-architecture.md](08-memory-architecture.md) — one database to back up, encrypt, and access-control instead of two. Pinecone is rejected outright as a managed SaaS holding applicant-derived embeddings outside MARA's control.
- If retrieval latency or corpus scale outgrows pgvector (Dify supports Qdrant as a backend natively), migrate the Knowledge Service's vector backend to self-hosted Qdrant without touching any calling code, since retrieval is already behind the Knowledge Service API.

## 4.4 Backend, data, and infra

| Concern | Choice | Verdict | Alternatives considered | Why |
|---|---|---|---|---|
| Backend language/framework | Python + FastAPI | Reuse directly (matches OpenHands, LangGraph, CrewAI — all Python-native) | Node/NestJS, Go | One language across agents, tools, and services avoids a serialization boundary between "AI code" and "backend code"; FastAPI is already OpenHands' pattern |
| Primary datastore | PostgreSQL | Reuse directly | MySQL, MongoDB | Strong transactional guarantees for audit/approval records, native pgvector, mature Malaysia-hostable managed offerings |
| Object storage | S3-compatible (MinIO self-hosted / AWS S3) | Reuse directly | Local filesystem, Azure Blob | MinIO lets MARA run fully on-prem for data residency; API-compatible with AWS S3 if cloud is later approved |
| Cache / auxiliary queue | Redis + Celery | Reuse directly | Temporal (see above), Arq, RabbitMQ | Mature, well-understood, used only for ancillary async jobs (OCR batching, email dispatch, audio rendering) — the agentic workflow durability itself is LangGraph's job, not the queue's |
| Auth / identity | Keycloak | Reuse directly | Auth0/Okta (SaaS), custom | Open-source, self-hostable, native RBAC/ABAC and SSO/SAML/OIDC federation with a future government IdP; avoids per-seat SaaS identity cost and data-residency exposure |
| Containerization | Docker | Reuse directly | — | Already the OpenHands convention (`containers/`, `docker-compose.yml`) |
| Orchestration | Kubernetes | Reuse directly (production), docker-compose (dev) | Docker Swarm, Nomad | OpenHands already ships a `kind/` (K8s) folder; K8s is the mainstream choice MARA's IT team is likeliest to already operate or be able to hire for |
| CI/CD | GitHub Actions + ArgoCD (GitOps) | Reuse directly (Actions), Reuse directly (ArgoCD) | GitLab CI, Jenkins | Actions already used by OpenHands (`.github/`); ArgoCD gives auditable, git-tracked production deploys — itself an audit-trail asset |
| Secrets | HashiCorp Vault (target), K8s Secrets + SOPS (interim) | Reuse directly | Cloud KMS-only | Vault decouples secret management from any single cloud vendor, consistent with the data-residency/self-host constraint in [01-vision.md](01-vision.md); SOPS-encrypted K8s secrets are the pragmatic interim step before Vault is operationally justified |

## 4.5 Observability

| Concern | Choice | Verdict | Why |
|---|---|---|---|
| Tracing | OpenTelemetry | Reuse directly | Vendor-neutral instrumentation standard; avoids locking trace data to one backend |
| Metrics | Prometheus + Grafana | Reuse directly | De facto K8s-native standard, well-documented, self-hostable |
| Logs | Grafana Loki (or ELK as fallback) | Reuse directly | Pairs natively with Grafana/Prometheus for a single pane of glass; ELK considered if MARA's IT team already runs it |
| LLM/agent-specific observability | Langfuse (self-hosted) | Reuse directly | Purpose-built for LLM tracing, prompt versioning, and cost tracking (Phase 12) — general APM tools don't natively understand token cost or prompt/response pairs |

## 4.6 Domain tools

| Tool | Choice | Verdict | Why |
|---|---|---|---|
| OCR | PaddleOCR / Tesseract (self-hosted), cloud Document AI as opt-in for non-sensitive docs | Reuse directly (self-hosted primary) | Malay-language support, data residency for identity/financial documents; cloud OCR gated behind explicit document-sensitivity classification (see [11-security-architecture.md](11-security-architecture.md)) |
| Word/Excel/PowerPoint generation | python-docx, openpyxl, python-pptx | Reuse directly | Mature, widely used, no licensing dependency on Microsoft Office being installed server-side |
| Speech-to-text | Whisper (self-hosted) | Reuse directly | Strong Malay/English code-switch performance, self-hostable for sensitive audio (officer dictation, briefings) |
| Text-to-speech | Piper/Coqui (self-hosted, default) with a cloud TTS opt-in for non-sensitive general narration | Reuse directly (self-hosted primary) | Same data-residency logic as OCR; cloud TTS only for content with no PDPA exposure |
| Web/external search | Tavily or Brave Search API, allow-listed domains, fully logged | Reuse directly | Purpose-built for LLM-agent search grounding (Tavily) or privacy-respecting general search (Brave); every call audited since it's the one tool category that reaches outside MARA's boundary |
| LLM provider | Anthropic Claude (Sonnet/Opus/Haiku family) via API or AWS Bedrock, with a self-hosted open-weight fallback path (vLLM) for maximum-sensitivity processing | Reuse directly (Claude primary) | Bedrock option gives a data-residency-controlled deployment path; OpenHands' existing LiteLLM abstraction (already in the codebase) is reused so provider choice stays swappable per agent/workload rather than hardcoded |

### 4.6.1 Model tiering (added in v1.0)

LLM token cost is the dominant cost driver in this platform (review board, [review/04-compliance-scale-cost-review.md](review/04-compliance-scale-cost-review.md) §10.1), and it scales with agent call volume, not officer headcount — so which model tier each agent uses is an explicit architectural decision, not left to "use one capable model everywhere," which is the single most expensive default. Routing is implemented in `shared/llm/` as part of the LiteLLM abstraction above:

| Tier | Model class | Used by |
|---|---|---|
| High-volume, lower-ambiguity | Haiku-class | Document Agent (classification/extraction — high call volume, narrower judgment per call) |
| Synthesis / policy interpretation | Sonnet-class | Compliance, Finance, Risk, Market Agents |
| Highest-stakes, lowest-volume | Opus-class, if used at all | Recommendation Agent only — the one agent where call volume is low enough and stakes high enough to justify the largest tier |

Reclassified services ([05-agent-architecture.md](05-agent-architecture.md) §5.14) that still need any LLM call at all (e.g., the Audit-query service's optional narrative-summarization layer) default to the smallest capable tier, since none of them perform ambiguous judgment that would justify a larger model.

## 4.7 Full reuse/fork/inspire/replace matrix

| Baseline project | Verdict | Scope of reuse |
|---|---|---|
| OpenHands | **Extract & customize** | Event stream, sandboxed tool execution, MCP host, secrets, session/user auth — as a library boundary, not `frontend/`'s screens or `enterprise/` |
| CrewAI | **Inspiration only** | Agent definition shape (role/goal/tools), applied only to the 7 true agents, not the runtime/orchestrator |
| LangGraph | **Reuse directly** | Workflow engine: bounded state-graph templates, checkpointing, branching, human-in-the-loop pauses |
| LibreChat | **Inspiration only** | Conversation UX, file upload, multi-model picker patterns, applied to the new `apps/officer-workspace/` |
| Dify | **Reuse directly (isolated service, own database instance)** | Knowledge ingestion, chunking, dataset admin, retrieval API — not its agent/app builder |
| openhands-ui | **Reuse directly** *(added in v1.0)* | Design-system/component base for `apps/officer-workspace/` |
