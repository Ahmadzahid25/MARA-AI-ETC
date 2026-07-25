« [Index](00-INDEX.md) | Phase 5 of 16 »

# Phase 5 — Agent Architecture

> **v1.0 note:** this phase was revised per the Architecture Review Board's finding ([review/02-agent-and-tool-review.md](review/02-agent-and-tool-review.md) §4) and ACCB Condition C-2. The original draft treated all 12 proposed components as full LLM-reasoning agents. Five do deterministic transformation or orchestration work, not ambiguous judgment, and are reclassified as **services** in §5.11 below: Supervisor, the merged Report+Presentation ("Publishing") service, Voice, and (mostly) Audit. This document now specifies **7 true agents** (§5.2–5.9) and the 5 reclassified services (§5.11), governed by the single test in §5.14.

## 5.1 Common agent contract

Every agent below is a configuration of the same underlying Agent Runtime ([04-technology-stack.md](04-technology-stack.md)), not a bespoke codebase. Each is defined by:

- **Role/goal/backstory** (CrewAI-style definition) compiled into a system prompt.
- **Allowed tools**: an explicit allow-list from [06-tool-architecture.md](06-tool-architecture.md); an agent has zero implicit tool access.
- **Memory scope**: which of the six memory kinds ([08-memory-architecture.md](08-memory-architecture.md)) it can read/write, and at what granularity (own task only vs. shared workflow state).
- **Confidence threshold**: a numeric self-reported confidence below which the agent must escalate rather than emit a result as final.
- **Escalation target**: which role (Supervisor, specific human role, or another agent) receives an escalation.
- **Communication protocol**: agents never call each other directly — all inter-agent communication is a typed message posted to the Workflow Engine's shared state, read by the Supervisor and routed per the workflow graph. This is what keeps the audit trail complete (see [02-system-architecture.md](02-system-architecture.md)) and prevents agents from forming undocumented direct dependencies on each other.

Every agent output includes a **provenance block**: source document/tool-call IDs backing each claim, and a self-reported confidence score. An output with no provenance for a factual claim is a defect, not a style choice — this is what makes [01-vision.md](01-vision.md)'s "zero silent unsupported claims" success criterion enforceable in code review and in automated eval, not just policy. As of v1.0, provenance is not trusted on the agent's say-so alone: the Tool Runtime deterministically verifies every cited document/chunk ID against the actual tool-call results returned during that task before the output reaches a human ([06-tool-architecture.md](06-tool-architecture.md)) — closing the gap where an agent could emit a well-formed but fabricated citation that passed schema validation without ever having been retrieved.

## 5.2 Planner

| Attribute | Definition |
|---|---|
| Responsibilities | Select and parameterize a bounded, versioned workflow template for an officer's stated objective — **not** freely construct new task-graph topology at runtime (see 5.2.1) |
| Inputs | Officer's natural-language objective, workflow type selection, attached source documents |
| Outputs | A workflow instance: a reference to the selected template plus its parameters, handed to the Supervisor/Workflow Engine |
| Memory | Reads: Knowledge Memory (workflow templates, policy). Writes: Task Memory (the selected template + parameters) |
| Allowed tools | Knowledge/RAG query (to check applicable policy/workflow templates); no execution tools |
| Permissions | Read-only against all data sources; cannot itself invoke Document/Finance/etc. agents — only selects and parameterizes the template |
| Escalation rules | If the objective is ambiguous or matches no known workflow template with confidence ≥ threshold, escalate to the requesting officer for clarification before planning |
| Failure handling | On planning failure (malformed objective, no applicable template), returns a structured error with suggested next steps rather than a best-guess plan |
| Confidence threshold | 0.75 template-match confidence; below this, ask a clarifying question instead of guessing the workflow |
| Human approval | Selected template and parameters are shown to the initiating officer before execution begins (not a blocking approval gate for low-risk workflows, but always visible) |
| Communication | Emits the selected-template reference as workflow-engine state; does not talk to downstream agents directly |

### 5.2.1 Why bounded template selection, not free graph construction (added in v1.0)

This constraint was added per Review Board Finding A1 ([review/01-architecture-and-foundation-review.md](review/01-architecture-and-foundation-review.md) §1.2) and is load-bearing, not stylistic. LangGraph `StateGraph`s are normally compiled from code at build time; an LLM freely emitting novel executable orchestration topology at runtime is a materially riskier system than one selecting among pre-built, tested, version-controlled templates — a malformed or adversarially-influenced "plan" could, in principle, produce a graph that skips a mandatory approval node, and that is not a risk prompting alone can be trusted to prevent. Concretely: the Planner's output is validated against the referenced template's declared schema before it reaches the Supervisor — any reference to a node type or edge not present in that schema is rejected, not merely discouraged. The bounded template set lives in `workflows/` ([03-repository-structure.md](03-repository-structure.md)) and is exactly the eight templates catalogued in [07-workflow-architecture.md](07-workflow-architecture.md) §7.3.

## 5.3 Document Agent

| Attribute | Definition |
|---|---|
| Responsibilities | Extract structured data (identity fields, financial figures, dates, entities) from submitted documents; classify document type |
| Inputs | Raw document files (PDF/image/scan) from Object Storage |
| Outputs | Structured extraction records with per-field confidence and source bounding-box/page citation |
| Memory | Writes: Task Memory (extraction results), Shared Memory (for downstream Finance/Compliance agents) |
| Allowed tools | OCR, PDF parsing, document classification (see [06-tool-architecture.md](06-tool-architecture.md)) |
| Permissions | Read access to the specific document set assigned to its task only, not the full document repository |
| Escalation rules | Any field extracted below confidence threshold is flagged, not guessed; escalates to officer for manual entry/confirmation |
| Failure handling | Illegible/corrupt documents are flagged as extraction-failed with the specific page/reason, not silently skipped |
| Confidence threshold | 0.85 per extracted field; below this the field is marked "unverified" and blocks downstream Finance Agent calculations that depend on it |
| Human approval | Low-confidence extractions require officer confirmation before use in any downstream calculation or claim |
| Communication | Publishes extraction records to Shared Memory keyed by document ID, consumed by Finance/Compliance/Risk agents |
| Model tier (v1.0) | Haiku-class — high call volume, narrower judgment per call ([04-technology-stack.md](04-technology-stack.md) §4.6.1) |

## 5.4 Compliance Agent

| Attribute | Definition |
|---|---|
| Responsibilities | Cross-check application data and documents against MARA policy and regulatory requirements; surface compliance gaps/exceptions |
| Inputs | Structured extraction from Document Agent, applicant/application metadata, policy corpus (via Knowledge Base) |
| Outputs | Compliance checklist with pass/fail/exception per requirement, each citing the specific policy clause |
| Memory | Reads: Shared Memory (extractions), Knowledge Memory (policy). Writes: Task Memory, Audit Memory (compliance findings are audit-significant by nature) |
| Allowed tools | RAG/knowledge query, structured database query (for existing applicant history) |
| Permissions | Read-only; cannot alter application records, only report findings |
| Escalation rules | Any hard policy violation (disqualifying) escalates immediately to a Compliance Officer, halting workflow progression toward approval until resolved |
| Failure handling | If policy corpus lookup is inconclusive (no matching clause), reports "no applicable policy found" explicitly rather than inferring one |
| Confidence threshold | 0.9 for auto-pass classification; anything lower routes to manual compliance review |
| Human approval | Hard violations always require Compliance Officer sign-off; soft/advisory flags are surfaced but don't block |
| Communication | Publishes compliance checklist to Shared Memory; triggers a workflow-level escalation event on hard violations |
| Model tier (v1.0) | Sonnet-class — policy interpretation requires genuine synthesis ([04-technology-stack.md](04-technology-stack.md) §4.6.1) |

## 5.5 Finance Agent

| Attribute | Definition |
|---|---|
| Responsibilities | Perform financial analysis (ratios, cash flow assessment, loan-to-value, repayment capacity) from extracted figures |
| Inputs | Structured financial extraction from Document Agent, loan/grant product parameters |
| Outputs | Financial analysis report with every figure traced to source extraction and every derived number traced to a specific calculation tool call |
| Memory | Reads: Shared Memory. Writes: Task Memory |
| Allowed tools | Deterministic calculation tools only for arithmetic (never LLM mental math for figures that inform a decision — see [06-tool-architecture.md](06-tool-architecture.md)), RAG query for product terms |
| Permissions | Read-only on extraction data; cannot modify source documents or figures, only compute from them |
| Escalation rules | If required source figures are missing or below Document Agent confidence threshold, escalates rather than computing on unverified input |
| Failure handling | A failed/ambiguous calculation input halts that specific calculation with a clear reason, not a best-effort estimate presented as fact |
| Confidence threshold | N/A for the arithmetic itself (deterministic); 0.85 for qualitative judgments (e.g., "repayment capacity assessment") |
| Human approval | All financial conclusions feeding a committee report require Finance Officer review before the report is finalized |
| Communication | Publishes financial analysis to Shared Memory, consumed by Risk and Recommendation agents |
| Model tier (v1.0) | Sonnet-class — interpreting calculation results is genuine synthesis, even though the arithmetic itself is deterministic tool output ([04-technology-stack.md](04-technology-stack.md) §4.6.1) |

## 5.6 Risk Agent

| Attribute | Definition |
|---|---|
| Responsibilities | Synthesize Document/Compliance/Finance/Market outputs into a risk profile and risk rating |
| Inputs | Shared Memory outputs from Document, Compliance, Finance, and Market agents |
| Outputs | Risk rating with component breakdown (financial, compliance, market risk) and citations to each contributing agent's output |
| Memory | Reads: Shared Memory (all upstream agent outputs). Writes: Task Memory |
| Allowed tools | RAG query (historical precedent, risk policy), calculation tools for risk-scoring formulas |
| Permissions | Read-only aggregator; produces no new primary data, only synthesis |
| Escalation rules | Escalates to Risk Officer if component inputs disagree materially (e.g., strong financials but a hard compliance flag) rather than auto-resolving the conflict |
| Failure handling | If any required upstream agent output is missing, the risk rating is marked "incomplete — pending [X]" rather than computed on a partial picture |
| Confidence threshold | 0.8; below this the rating is presented as a range/qualitative flag rather than a single score |
| Human approval | Risk rating is always officer-reviewed before it reaches committee materials — it directly informs approval decisions |
| Communication | Publishes risk profile to Shared Memory, consumed by Recommendation and the Publishing service (§5.11) |
| Model tier (v1.0) | Sonnet-class — cross-agent synthesis under potentially conflicting evidence ([04-technology-stack.md](04-technology-stack.md) §4.6.1) |

## 5.7 Market Agent

| Attribute | Definition |
|---|---|
| Responsibilities | Gather external market context (industry trends, comparable business performance, sector risk) relevant to the applicant's business |
| Inputs | Applicant business sector/description, geographic market — **generalized, never the applicant's identifying details** (see 5.7.1) |
| Outputs | Market context brief with every claim cited to a specific external source and retrieval date |
| Memory | Writes: Task Memory, Knowledge Memory (cache reusable market findings for future applications in the same sector, subject to freshness expiry **and the same document-lifecycle approval gate as other Knowledge Memory content** — see [09-knowledge-architecture.md](09-knowledge-architecture.md) §9.7) |
| Allowed tools | Web/external search (allow-listed domains only, with mandatory query sanitization — see [06-tool-architecture.md](06-tool-architecture.md)), RAG query against previously ingested market data |
| Permissions | The only agent with outbound external-network tool access; every call logged with query and domains hit; network-policy-enforced at the infrastructure level so no other component can acquire a second egress path (see [11-security-architecture.md](11-security-architecture.md) §11.7) |
| Escalation rules | If search yields no credible sources, reports "insufficient external data" rather than an LLM-generated market narrative unsupported by a citation |
| Failure handling | Search API failure/timeout degrades to Knowledge Base-only results with an explicit note that live search was unavailable |
| Confidence threshold | 0.7 source-credibility threshold per claim; lower-credibility sources are labeled, not excluded silently |
| Human approval | Not independently gated, but always visible in the final report for officer judgment given its inherently less certain nature than internal document data |
| Communication | Publishes market brief to Shared Memory, consumed by Risk and Recommendation agents |
| Model tier (v1.0) | Sonnet-class — query formulation and source-credibility judgment are genuine reasoning tasks ([04-technology-stack.md](04-technology-stack.md) §4.6.1) |

### 5.7.1 Query sanitization — mandatory, not optional (added in v1.0)

Per Review Board Finding B3 ([review/02-agent-and-tool-review.md](review/02-agent-and-tool-review.md) §5.3) and ACCB Mandatory Change 1: restricting external egress to this one agent's tool prevents *other* agents from leaking data externally, but says nothing about *what this agent's own queries contain*. A Market Agent constructing a search query using the applicant's actual business name, owner's name, or other identifying detail would leak PII to an external provider even with the egress restriction fully respected — the restriction constrains the door, not what walks through it. This agent **must not ship** without the search tool itself (not agent-prompted discipline) enforcing sanitization: queries are generalized to sector/industry/region terms before leaving the platform, verified programmatically at the Tool Runtime. This is a precondition for the Market Agent's existence in any environment processing real applicant data, gating Milestone 3 — see [14-roadmap.md](14-roadmap.md).

## 5.8 Recommendation Agent

| Attribute | Definition |
|---|---|
| Responsibilities | Synthesize all upstream agent outputs into a draft recommendation (approve/decline/approve-with-conditions) for officer consideration |
| Inputs | Shared Memory: Document, Compliance, Finance, Risk, Market outputs |
| Outputs | Draft recommendation with explicit reasoning trail — this is a *draft for officer judgment*, never a final decision |
| Memory | Reads: Shared Memory (all upstream outputs). Writes: Task Memory |
| Allowed tools | None beyond RAG query for precedent lookup — this agent reasons over already-gathered evidence, it does not gather new evidence |
| Permissions | Cannot finalize or transmit a decision anywhere; output is inert until an officer acts on it |
| Escalation rules | Escalates (declines to recommend) if any upstream agent flagged a hard compliance violation, or if overall confidence is below threshold — presents the evidence and explicitly declines to suggest an outcome rather than guessing |
| Failure handling | Missing upstream input results in "recommendation withheld pending [X]," never a recommendation computed on a partial picture |
| Confidence threshold | 0.8; below this, output is explicitly labeled "low-confidence — manual assessment recommended" rather than suppressed, so the officer sees why |
| Human approval | **Always** requires explicit officer approval before entering a committee report — this is the highest-stakes agent output in the system and is never auto-forwarded |
| Communication | Publishes draft recommendation to Task Memory; visible only through the Review & Approval Console, never auto-transmitted downstream |
| Model tier (v1.0) | The one agent where Opus-class (if used at all) is cost-justified — lowest call volume, highest stakes ([04-technology-stack.md](04-technology-stack.md) §4.6.1) |

## 5.9 Agent summary table

| Agent | Confidence threshold | Human approval | Model tier |
|---|---|---|---|
| Planner | 0.75 (template match) | Plan visible, not always blocking | Haiku-class |
| Document Agent | 0.85 (per field) | Required on low-confidence extraction | Haiku-class |
| Compliance Agent | 0.9 (auto-pass) | Required on hard violations | Sonnet-class |
| Finance Agent | 0.85 (qualitative judgments) | Required before report finalization | Sonnet-class |
| Risk Agent | 0.8 | Always officer-reviewed | Sonnet-class |
| Market Agent | 0.7 (source credibility) | Visible, not independently gated | Sonnet-class |
| Recommendation Agent | 0.8 | Always required, never auto-forwarded | Opus-class (only agent) |

## 5.10 Supervisor (reclassified — see §5.14)

Supervisor is **not** an agent as of v1.0. It is deterministic control logic — dispatch, per-agent budget/permission enforcement, retry-vs-escalate-vs-fail policy evaluation — implemented as LangGraph control flow, with no LLM prompt, confidence threshold, or escalation-target concept of its own. It has no ambiguous judgment to make: every decision it takes (retry this task, escalate that one, mark a workflow blocked) is policy evaluation over already-known state, not reasoning over uncertain input.

| Attribute | Definition |
|---|---|
| Responsibilities | Runtime coordination of the selected workflow template: dispatch tasks to agents, enforce per-agent tool/budget limits, monitor timeout/failure, decide retry vs. escalate vs. fail-workflow |
| Inputs | Selected workflow template + parameters from Planner, live agent status/results, tool-runtime error signals |
| Outputs | Dispatch commands, retry decisions, escalation events, workflow status updates |
| Memory | Reads/writes: Task Memory, Shared Memory (workflow-wide state). Writes: Audit Memory (every dispatch/retry/escalation decision) |
| Permissions | Can invoke any agent within the active workflow template's declared graph; cannot invoke agents outside that graph (prevents scope creep mid-workflow — this is also what closes Red Team finding #3 in [review/03-data-and-security-review.md](review/03-data-and-security-review.md)) |
| Failure handling | Configurable per-task retry policy (default: 2 retries with backoff); on exhaustion, the task is marked failed and the workflow pauses for human intervention rather than silently proceeding with a downstream agent on incomplete input; a circuit breaker trips on systemic (not per-task) LLM/provider degradation, pausing new dispatch platform-wide rather than letting every in-flight workflow retry independently |
| Human approval | Escalations always route to a human; the Supervisor never resolves a low-confidence result itself |
| Implementation location | `services/supervisor_service/`, not `agents/` ([03-repository-structure.md](03-repository-structure.md)) |

## 5.11 Reclassified services (formerly Report, Presentation, Voice, Audit Agents)

Per Review Board Part 2 ([review/02-agent-and-tool-review.md](review/02-agent-and-tool-review.md) §4) and ACCB Condition C-2, these four originally-proposed agents perform deterministic transformation of already-decided input, not ambiguous judgment, and are implemented as services in `services/` — see the reclassification test in §5.14.

### 5.11.1 Publishing Service (merged Report + Presentation)

| Attribute | Definition |
|---|---|
| Responsibilities | Assemble a committee-ready document and, on request, a presentation deck from approved upstream outputs (Document, Compliance, Finance, Risk, Market, Recommendation). Merged from two originally-separate agents because both are the same job — turn approved content into a distributable artifact — with two output renderers, not two identities |
| Inputs | Officer-approved agent outputs only (never drafts pending review) |
| Outputs | A Word/PDF committee report (`render_docx`) and/or a PowerPoint deck (`render_pptx`), citations preserved from source agents, deck speaker notes retaining citations |
| Memory | Reads: Shared Memory (approved outputs only). Writes: Task Memory |
| Allowed tools | Word/PDF generation, PowerPoint generation, chart/table rendering, RAG query for template/formatting standards |
| Permissions | Read-only on approved data; cannot include any agent output that hasn't passed its required human approval gate |
| Escalation rules | If required approved inputs are missing (e.g., Recommendation not yet approved) or report content doesn't map cleanly to slide structure, refuses/flags rather than drafting a placeholder or silently reconciling |
| Failure handling | Rendering failures surface the specific error to the officer, with underlying data preserved for retry |
| Human approval | Final report and deck require officer sign-off before distribution to the committee |
| Implementation location | `services/publishing_service/` |
| Optional narrative smoothing | If natural-language smoothing between sections is wanted, it is one constrained, template-bounded LLM call inside the service function — not an agentic tool-loop with its own confidence/escalation machinery |

### 5.11.2 Voice Service (formerly Voice Agent)

| Attribute | Definition |
|---|---|
| Responsibilities | Produce audio briefings (TTS narration of an approved report/summary) and accept dictated officer input (STT) — direct tool wrapping, no decomposition or judgment involved |
| Inputs | Approved report/summary text (TTS direction); officer audio input (STT direction) |
| Outputs | Audio file artifact (briefing) or transcribed text (dictation) with the model-native confidence score |
| Allowed tools | TTS, STT (see [06-tool-architecture.md](06-tool-architecture.md)) |
| Permissions | For STT, only processes audio explicitly submitted by an authenticated officer in an active session — no passive/background audio capture |
| Escalation rules | Low-confidence transcription (below 0.85) is returned to the officer for confirmation before being treated as input to any other component |
| Failure handling | Audio processing failure returns a clear error; never silently substitutes a guessed transcription |
| Human approval | STT output used to drive any action beyond dictation display requires officer confirmation of the transcript |
| Implementation location | `services/voice_service/`, backed directly by `tools/audio/` |

### 5.11.3 Audit Service (formerly Audit Agent)

| Attribute | Definition |
|---|---|
| Responsibilities | Structured, deterministic query API over Audit Memory for the common case (what happened, when, by whom); a thin, clearly-labeled LLM narrative-summarization layer sits on top **only** for producing a readable prose summary of already-correct structured query results — never as a substitute for the record, never with synthesis or inference over uncertain data |
| Inputs | Audit Memory records for a given workflow/conversation/time range |
| Outputs | Structured event list (primary, authoritative) plus, optionally, a human-readable narrative clearly labeled as a generated summary of the structured record above it |
| Memory | Reads: Audit Memory (read-only, separate credential path — see [11-security-architecture.md](11-security-architecture.md)). Writes: nothing to any operational memory — its own invocations are themselves audit-logged by the platform |
| Permissions | Read access spans workflows beyond the requesting officer's own — restricted to users holding an explicit Auditor role, checked at the Gateway and re-checked at the Memory service |
| Escalation rules | If Audit Memory has a gap (missing expected event), reports the gap explicitly — a gap is itself a finding, never silently smoothed over |
| Failure handling | Query failures are reported as such; never reconstructs history from inference when the record is unavailable |
| Human approval | Not applicable — read-only, no write/action capability to approve |
| Implementation location | `services/audit_service/`; the narrative layer is the one place in this section where an LLM call exists at all, and it defaults to the smallest capable model tier |

## 5.12 Reclassification impact on 06/07/09/10/11

Every phase document that referenced "Report Agent," "Presentation Agent," "Voice Agent," or "Audit Agent" as agents now refers to their service names (`publishing_service`, `voice_service`, `audit_service`) or, for Supervisor, `supervisor_service` — cross-references throughout this document set have been updated accordingly. The permission, audit-logging, and escalation discipline these components are subject to is unchanged by the reclassification: a service enforces the same Tool Runtime permission checks and writes to the same Audit Memory as an agent would (see [02-system-architecture.md](02-system-architecture.md) §2.4). What changes is only whether the component carries an LLM-reasoning loop by default.

## 5.13 Why 7 agents and not fewer/more

Each remaining agent boundary corresponds to either a distinct evidentiary domain (Document/Finance/Compliance/Market each pull from a different source-of-truth and need independently tunable confidence thresholds) or a distinct trust boundary (Market Agent is the only one with outbound network access). Merging, e.g., Finance and Risk into one agent would mix a deterministic-calculation trust profile with a synthesis/judgment trust profile, making it harder to reason about what confidence threshold or approval gate applies to which part of the output. Splitting further (e.g., separate agents per document type) is deferred until evidence from Milestone 1 usage shows the Document Agent's scope is actually a bottleneck — see [14-roadmap.md](14-roadmap.md).

## 5.14 The agent-vs-service test (added in v1.0)

Before adding any new component to `agents/` rather than `services/`, apply the test the Review Board used to reclassify the original twelve ([review/02-agent-and-tool-review.md](review/02-agent-and-tool-review.md) §4): **does this component make a genuinely ambiguous judgment call that requires weighing conflicting or incomplete evidence, or does it execute a well-defined transformation of already-decided input?** The former belongs in `agents/`, carries the full Agent Runtime (LLM-reasoning loop, confidence threshold, escalation policy). The latter belongs in `services/` — it either has no meaningful confidence score to miscalibrate (deterministic code either produces the right output or throws a typed error), or, if it needs any LLM call at all, that call is narrowly scoped and does not need the full agent apparatus around it. This test is binding for all future component additions, not just the original twelve — see [05-development-guidelines.md](../repo-audit/05-development-guidelines.md) §5.6.

## 5.15 Where autonomy is declared (added in v1.0)

§5.1 defines what every agent declares — allowed tools, confidence threshold, escalation target. This section fixes *where* those declarations live, because the answer determines how safely they can be changed later.

### 5.15.1 One registry, not per-agent constants

Every autonomy decision for every agent is declared in `shared/agent_profiles/` and nowhere else: the tool grant, the autonomy level (§5.15.2), the confidence floor, the approval gate, and whether the profile may reach the network. Tool modules derive their own caller allow-lists from that registry rather than restating them, so the two directions of the same permission relationship — "this agent may call OCR" and "OCR accepts this caller" — cannot disagree.

This mirrors the reasoning already applied to model tiering in [04-technology-stack.md](04-technology-stack.md) §4.6.1 ("deliberately data, not code"), extended to the rest of the autonomy surface, and it is load-bearing for the same reason: a decision spread across N modules is a decision nobody can review as a whole, and one that drifts silently when only some of the N are updated. `shared/llm/model_tiers.py` remains the single authority for the per-agent model tier — the profile registry defers to it rather than duplicating it.

Adjusting an agent's autonomy is therefore a reviewable one-file diff, and the invariants below are enforced in `tests/unit/mara/test_agent_profiles.py` rather than left to reviewer vigilance.

### 5.15.2 Autonomy levels

The tool grant and the latitude an agent has *within* that grant are separate dials, because they are separate risks:

| Level | Meaning | Applies to |
|---|---|---|
| `BOUNDED` | The workflow template's node decides what runs and in what order; the agent contributes judgment at one step but does not choose the next one. | All seven agents today — the Agent Runtime's action/observation loop (§5.1, [02-system-architecture.md](02-system-architecture.md) Layer 4) is not built yet, and the registry records the level the current implementations actually have rather than the one they aspire to. |
| `GUIDED` | The agent chooses tools and ordering freely, iterating tool → observation until it emits a result — strictly inside its grant, with the same confidence floor and approval gate applied to the output. | The intended level for the seven agents once the Agent Runtime lands. Widening *how* an agent works without widening what it can reach or weakening what a human signs off. |
| `EXPLORATORY` | Full agentic loop, broad grant, no confidence gate. | Permitted only on a profile barred from the decision path — see §5.15.3. |

The distinction matters because `BOUNDED` → `GUIDED` is a genuinely cheap change (reach and oversight are unchanged) while lowering a confidence floor or loosening an approval gate is a policy change to the guarantees in [01-vision.md](01-vision.md). Keeping them as separate fields is what stops "make the agent more capable" from silently meaning the second one.

### 5.15.3 The exploration sandbox

Open-ended analytical work — an officer exploring a portfolio question with no predetermined shape — is a real need that the bounded-template model (§5.2.1) deliberately does not serve. The registry answers it with a profile, `exploration_sandbox`, that carries `EXPLORATORY` autonomy and no confidence gate, and pays for that latitude with `can_inform_decision = False`.

That flag is the whole design. Its output may not enter a workflow decision, an approval record, or a committee report, and the bar is structural — decision-path code calls `assert_can_inform_decision()` rather than each caller re-deciding — not a matter of officer discipline or a label in the UI. The sandbox is correspondingly **not** an eighth agent: it holds no position in any workflow template, appears in no entry of §7.3's catalogue, and is deliberately excluded from `AgentName`, which remains the seven agents §5.14 recognises.

It is also not granted external egress. Sole-egress stays the Market Agent's (§5.7); a broadly-permissioned sandbox is precisely where a second egress path would otherwise be acquired by accident, which is what §11.7's network policy exists to prevent.
