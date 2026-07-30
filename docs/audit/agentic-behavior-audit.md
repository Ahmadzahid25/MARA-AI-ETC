# Agentic Behavior Audit — MARA AI-ETC

**Date:** 2026-07-29
**Scope:** Prompt architecture, LangGraph workflows, state & memory, tool orchestration, knowledge retrieval, agent collaboration, planning & reflection, response generation.
**Status:** Audit only — no code changes made.

---

## 1. Executive summary

The system does not behave agentically because, structurally, **it is not an agentic system yet — and one critical bug makes it look even less agentic than it actually is.**

Three facts dominate everything else in this report:

1. **`TieredLLMClient` silently swallows *every* LLM error and returns hardcoded canned strings** (`shared/llm/client.py:50-51,71-72`). If the API key is missing, misconfigured, rate-limited, or any transient error occurs, every "agent" in the platform returns the same fixed mock text (`'0.85'`, one fixed 3-field extraction JSON, `'0.88'`) — with no log line, no flag, no error. If your deployment has ever run without a working `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, **you have been watching hardcoded strings, not an AI**. This alone can explain "responses are repetitive and often follow the same wording," "different requests produce very similar reasoning," and "all agents have identical personalities."

2. **No agent has an agentic loop.** Every agent is a single-shot `complete_for_agent()` call with a hand-built prompt string that demands a rigid JSON shape ("Respond with the JSON object only, no other text"). There is no native tool-calling, no action→observation iteration, no multi-turn reasoning. The codebase itself is honest about this: every profile is `AutonomyLevel.BOUNDED` and the docstrings repeatedly say "the (not-yet-built) Agent Runtime" (`shared/agent_profiles/profiles.py:59-65`, every `agents/*/` class docstring). Tools are invoked by deterministic Python code in workflow nodes, never *chosen* by a model. The "multi-agent system" is, exactly as you suspected, **seven single-purpose LLM calls wrapped in Python functions, sequenced by a fixed graph.**

3. **The chat entry point has no memory and cannot actually do anything.** `services/api_gateway/routers/chat.py` constructs a fresh `Planner()` per request, passes only the current message (no conversation history, no thread), and — per its own `NOTE` at line 91-98 — **never dispatches a workflow at all**. Every workflow-intent message gets the same hardcoded reply: *"I'm ready to start a **{template}** workflow. Please attach the document using the + button…"* — a literal fixed template response, which is precisely the experience you described.

The good news: the underlying scaffolding is unusually solid for this stage — real LangGraph graphs with a Postgres checkpointer and durable `interrupt()` approval gates, a clean tool-permission registry, provenance-verified citations, model tiering. The platform has excellent *governance* architecture and almost no *agency* architecture. The remediation path (§5) is about adding the agency layer the docs already promise, not rebuilding.

### Symptom → root cause map

| Observed symptom | Primary root cause | Finding |
|---|---|---|
| 1. Repetitive, same-wording responses | Silent mock fallback; hardcoded chat reply; rigid JSON-only prompts | C-1, C-3, H-6 |
| 2. Similar reasoning across different requests | Same single-shot prompt template per agent; no temperature/diversity; mock fallback | H-1, H-6, C-1 |
| 3. Rarely asks clarifying questions | Clarification exists but is a dead end — no conversation state to receive the answer | C-2 |
| 4. Answers immediately, never plans | Planner is an intent classifier over 8 static templates, not a planner | H-2 |
| 5. Identical agent personalities | 6 of 7 agents have **no system prompt at all** | H-3 |
| 6. "Multiple prompts around one LLM," not collaborating agents | No agent runtime; agents exchange only scores/enums, reasoning discarded | H-1, H-5 |
| 7. Static tool usage | Tools hardwired in workflow-node code; model never sees a tool list | H-1, H-4 |
| 8. Less intelligent than Claude Code/Copilot | All of the above: those systems are model-driven loops; this is code-driven sequencing | §6 |

---

## 2. Findings

Severity scale: **Critical** (defeats the system's purpose or integrity), **High** (directly causes the observed non-agentic behavior), **Medium** (materially limits quality/adaptivity), **Low** (hygiene).

---

### C-1 · CRITICAL — LLM client silently replaces every failed call with canned mock data

**Where:** `shared/llm/client.py:50-51`, `71-72`, `_mock_dev_response` at `74-94`.

```python
try:
    model = self._tier_model_config.model_for_agent(agent)
    return await litellm.acompletion(model=model, messages=messages, **litellm_kwargs)
except (Exception, litellm.AuthenticationError):   # catches EVERYTHING
    return self._mock_dev_response(str(agent), messages)
```

**Root cause:** a dev-convenience fallback was wired into the production code path with a blanket `except Exception` (the `litellm.AuthenticationError` in the tuple is redundant — `Exception` already covers it). The mock returns fixed strings: `'0.85'`, one hardcoded 3-field extraction (`"Syarikat Usahawan Bumiputera Sdn Bhd"`, `"RM 250,000"`…), `'0.88'`.

**Why it kills agentic behavior:**
- Any auth/config/network/rate-limit failure makes **every agent return identical canned output on every request**, silently. This is the single most plausible explanation for symptoms 1, 2, and 5 as experienced.
- It defeats every carefully built safeguard downstream. All seven agents have `*ParsingError` classes documented as "surfaced, never silently defaulted" — but the client silently defaults *before* they can fire.
- It is also a **data-integrity hazard**: fabricated financial figures can flow into a real loan assessment with no marker distinguishing them from model output.

**Recommendation (P0, ~1 hour):** delete the fallback from the production path. Let errors propagate (the Supervisor's `dispatch_task` retry/circuit-breaker in `services/supervisor_service/supervisor_service.py` exists precisely to handle them — today it can never see a failure). If a mock mode is wanted for local dev, gate it behind an explicit setting (`MARA_LLM__MOCK_MODE=true`) that refuses to activate outside dev, and log loudly on every mock response.

---

### C-2 · CRITICAL — The conversational entry point is stateless: no history, no thread, no follow-up

**Where:** `services/api_gateway/routers/chat.py:64-67`; `agents/planner/planner.py:226-244`.

**Root cause:** `chat()` builds `Planner()` per request and calls `planner.plan(body.message)` with the raw single message. There is no conversation ID, no message history, no persisted chat state anywhere in the gateway (the Postgres checkpointer stores *workflow* state only; `services/memory_service` stores only extraction-calibration events).

**Why it kills agentic behavior:**
- The Planner *does* generate clarification questions (`planner.py:273-299`) — but they are dead ends. When the officer answers "yes, the loan one," the next request arrives with zero context; the answer is classified from scratch as a brand-new vague message. This is why the system *feels* like it never asks clarifying questions: asking is pointless when it can't hear the answer, and vague follow-ups loop back to the same canned clarification text.
- Multi-turn behavior — the defining trait of Claude Code/Copilot-style agents — is structurally impossible: no context accumulates, no plan persists, no prior reasoning is available.

**Recommendation (P0):** introduce a `conversation_id`, persist message history (a `chat_messages` table beside the existing vertical-slice store, or a LangGraph conversation graph checkpointed by the existing `AsyncPostgresSaver`), and pass the trailing window of turns to the Planner. A pending clarification should be stored as state so the next message is interpreted *as an answer to it* (slot-filling), not as a fresh utterance.

---

### C-3 · CRITICAL — Chat never dispatches workflows; the "workflow_started" reply is a hardcoded template

**Where:** `services/api_gateway/routers/chat.py:91-107`.

**Root cause:** acknowledged stub — the comment says workflow dispatch "is not yet wired in this slice." Every successfully classified workflow intent returns the same f-string: *"I'm ready to start a **{name}** workflow. Please attach the document using the + button…"*. Additionally, `planner.plan(body.message)` is called **without a `parameters` argument**, so even perfectly complete requests ("assess loan for document ABC-123") can never satisfy `required_parameters` — the planner cannot extract parameters from the message text (see H-2), and chat supplies none.

**Why it kills agentic behavior:** the one place officers talk to the system responds with (a) a mock string (C-1), (b) a canned clarification, or (c) a canned "attach the document" template. **There is no path through `/chat` that produces model-generated, situation-specific action.** The experience is repetitive because the reply space is finite and mostly hardcoded.

**Recommendation (P0/P1):** wire chat into the same app lifespan that already compiles the checkpointed graphs (`services/api_gateway/composition.py:63-79,156-183` proves the pattern); have the Planner extract parameters from the message (H-2); return real workflow status.

---

### H-1 · HIGH — No agent runtime: single-shot completions, no native tool use, no action/observation loop

**Where:** every agent: `agents/document_agent/document_agent.py:147-148`, `agents/compliance_agent/compliance_agent.py:225-226`, `agents/finance_agent/finance_agent.py:284-285`, `agents/market_agent/market_agent.py:256-257`, `agents/risk_agent/risk_agent.py:314`, `agents/recommendation_agent/recommendation_agent.py:277-278`, `agents/planner/planner.py:312`. Declared in `shared/agent_profiles/profiles.py:58-65` (`AutonomyLevel.BOUNDED` on all seven; `GUIDED` defined but unused).

**Root cause:** the architecture's Layer-4 "Agent Runtime" (action/observation loop) was never built; every agent is a Python function that (1) formats a string, (2) makes one `litellm.acompletion` call, (3) parses JSON. Which tools run, in what order, with what inputs is decided entirely by Python (`workflows/loan_assessment/loan_assessment.py` node functions), gated on things like `precedent_query is not None`. The model is never shown a tool list, never makes a `tool_use` call, never sees a tool result and reasons about it.

**Why it kills agentic behavior:** this is the definitional gap. "Autonomous tool selection," "dynamic planning," "adaptive reasoning" all require the model to be *in the loop* between tool calls. Today the model is a text-transformation step inside a deterministic pipeline — which is exactly why the system feels like "prompts wrapped around an LLM." Note the profile registry, tool allow-lists (`callers_allowed_for_tool`), and per-tool caller enforcement are **already built and are exactly what a runtime needs** — the guardrails exist; the loop they were designed to constrain doesn't.

**Recommendation (P1):** build the `GUIDED` runtime the profiles already anticipate: a loop that passes the agent's `allowed_tools` as native tool definitions (LiteLLM supports Anthropic/OpenAI tool calling uniformly), executes requested calls through the existing permission-checked tool modules, feeds results back, and iterates until the agent emits its typed result. Confidence floors and approval gates stay unchanged. Start with Market (already has two tools and degradation logic) or Compliance.

---

### H-2 · HIGH — The "Planner" is an intent classifier, not a planner

**Where:** `agents/planner/planner.py:77-126` (8 static templates), `143-164` (single classify-into-A-or-B prompt), `226-305`.

**Root cause:** deliberate v1 scoping ("select and parameterize a bounded, versioned workflow template… not freely construct new task-graph topology"). The one LLM call decides *converse vs. one-of-8-templates*. There is no task decomposition, no multi-step plan, no sequencing of templates, no parameter extraction from the message (parameters must arrive pre-structured; chat passes none — see C-3), and no plan artifact that later stages consume.

**Why it kills agentic behavior:** symptom 4 ("answers immediately instead of planning") is this by construction: there is nothing between "classify" and "execute fixed pipeline." A request that spans templates ("compare this application against the two similar ones we approved last month, then draft the committee note") is unrepresentable — it gets forced into one template or a clarification.

**Recommendation (P1):** keep the bounded catalogue (it's a sound governance choice) but make the Planner produce a real **plan object**: an ordered/parallel list of template invocations with extracted parameters, assumptions, and open questions, persisted in state. Parameter extraction from free text + attached-file context is the highest-value single upgrade. Multi-template composition can come later; extraction cannot.

---

### H-3 · HIGH — Six of seven agents have no system prompt, no role, no persona, no success criteria

**Where:** grep confirms exactly one `SYSTEM_PROMPT` in `agents/` — the Planner's (`planner.py:51-74`). All other agents send a bare `{'role': 'user', 'content': …}` (e.g. `recommendation_agent.py:277-278`, `risk_agent.py:314-316`).

**Root cause:** prompts were built as minimal data-in/JSON-out transformations. The user prompts themselves are terse data dumps with format directives ("Respond with a JSON object with exactly these keys… no other text").

**Why it kills agentic behavior:**
- Role, expertise, objectives, constraints, and success criteria — everything your audit request asks about — exist *only in docstrings and the architecture docs*, which the model never sees. The `AgentProfile` registry knows each agent's identity; the LLM doesn't.
- All seven "personalities" are therefore the same base model responding to near-identically shaped instructions — symptom 5 exactly.
- Suppressing all non-JSON text also suppresses reasoning: the model is denied space to think before committing to scores/decisions, degrading judgment quality *and* diversity.

**Recommendation (P1, cheap):** give each agent a system prompt derived from its profile + architecture section: role ("You are the Risk Officer's analytical counterpart…"), expertise, what upstream inputs mean, decision criteria, escalation duties, tone. Ask for reasoning *then* structured output (native tool-calling/structured-output beats "JSON only, no other text" — it removes the parsing fragility that motivated the rigidity).

---

### H-4 · HIGH — Fixed graph topology: one execution path, no revision loops, rejection is terminal

**Where:** `workflows/loan_assessment/loan_assessment.py:429-495` (topology), `348-356` (`_route_on`: anything not 'approved' → `completion`); same pattern in `workflows/document_assessment/`.

**Root cause:** the graph is a hand-wired pipeline. Conditional edges exist only for (a) approval-gate rejection → completion and (b) halt-after-risk. The module docstring itself flags it: "real re-run routing per §7.4 is a later refinement."

**Why it kills agentic behavior:**
- Every loan assessment runs the same stages in the same order regardless of content. Simple renewal and complex first-time application get identical treatment (identical cost, identical latency, identical output shape).
- A human rejection at any gate **ends the workflow** rather than triggering rework — the most valuable feedback signal in the system is discarded. There is no "revise its own conclusions" path anywhere (your area 7).
- Content-based branching (hard violation → deeper compliance dive; thin market data → extended search) is impossible because routers only read decision statuses, never analysis content.

**Recommendation (P1/P2):** add rework edges (rejection with `corrected_fields`/reason routes back to the producing node with the feedback in state); add content-conditional routing (e.g., `needs_fresh_search()` already exists on `RetrievalResult` — route Market to live search on it); longer-term, let the Planner's plan object parameterize which branches run.

---

### H-5 · HIGH — Upstream reasoning is discarded between nodes; the highest-stakes agent sees only aggregates

**Where:** `agents/recommendation_agent/recommendation_agent.py:99-122`; `agents/risk_agent/risk_agent.py:109-138`; `workflows/loan_assessment/loan_assessment.py:150-183` (state schema).

**Root cause:** inter-agent contracts are structured schemas that carry conclusions but not analysis. The Recommendation Agent — Opus-tier, "highest stakes" — receives literally:

```
Compliance: 3 requirement(s) checked, hard violation: False
Financial assessment: <one string> (confidence 0.82)
Risk rating: status=complete, components={...}, overall=0.41, range=None
Market: 5 claim(s), live_search_available=True
```

It never sees which compliance requirements passed/failed or why, any market claim text, any policy citation, or the risk assessor's rationale (the Risk Agent's LLM emits only four floats — its reasoning is never captured at all). `reasoning_trail` exists on `RecommendationOutput` but no upstream agent produces one.

**Why it kills agentic behavior:** this is why "agents don't build on each other's reasoning" (your area 6). The pipeline transports *verdicts*, so the final synthesis is a shallow function of a handful of numbers — producing generic, template-like recommendations no matter how rich the case is. It also wastes the Opus-tier spend.

**Recommendation (P1):** add a `reasoning`/`rationale` field to each agent's output schema (compliance item notes already exist — pass them through), and build the Recommendation/Risk prompts from the *full* upstream content (checklist items + notes, claim texts + credibility, financial figures, citations), not counts.

---

### H-6 · HIGH — Compliance checks are made against citation *references*, not policy *text*

**Where:** `agents/compliance_agent/compliance_agent.py:82-100`; `shared/schemas/knowledge.py:271-296`.

**Root cause:** `RetrievedChunk` carries `text`, but `PolicyCitation` (what the checker prompt receives) drops it — it keeps only `document_id`, `version`, `locator`, `relevance`. The check prompt renders `- document POL-7 v3, clause 4.2(b)` and then asks "Does the application satisfy this requirement?" The model **never sees the clause it is adjudicating against** and must answer from parametric memory of Malaysian lending policy.

**Why it kills agentic behavior (and correctness):** the retrieval pipeline — arguably the best-engineered part of the repo — is rendered useless at the point of judgment. Answers will be generic, low-variance, and unreliable; this materially contributes to "reasoning lacks adaptability" and is a correctness defect in a compliance product.

**Recommendation (P0/P1, small):** carry the chunk text into the check prompt (either add an `excerpt` field to `PolicyCitation`, or pass the `RetrievedChunk`s alongside the citations into `_build_check_prompt`). Provenance verification is unaffected — the ledger keys on refs, not text.

---

### M-1 · MEDIUM — No reflection, self-critique, or reviewer stage; gates run on single-shot self-reported confidence

**Where:** all agents (single completion, confidence parsed from the same response); thresholds in `shared/agent_profiles/profiles.py:177-249`; no critic node in either workflow graph.

**Root cause:** the architecture routes all review to *humans* (approval gates) and none to the *model*. A one-shot self-reported float is a weak, poorly calibrated signal, yet it gates escalation (0.7–0.9 thresholds). There is no draft→critique→revise pass anywhere, and no node re-examines an output before an officer sees it.

**Impact:** first-draft quality is final quality; officers become the only error-correction mechanism, which is expensive and slow. The calibration machinery (`services/memory_service/calibration.py`) exists but only records extraction corrections — it never feeds anything back into prompts or thresholds.

**Recommendation (P2):** add a reviewer step for the two `ALWAYS`-gated, decision-bearing outputs (Risk, Recommendation): a second pass (same tier or one tier down) that critiques the draft against the full upstream evidence, with one revision round. Close the calibration loop by injecting per-field historical correction rates into the Document Agent's prompt.

---

### M-2 · MEDIUM — Retrieval: deterministic query strings, small fixed `top_k`, optional invocation, no reformulation

**Where:** `agents/market_agent/market_agent.py:97-102` (`f'{sector} sector market outlook {region}'`); `rag_top_k: int = 3` defaults (`risk_agent.py:191`, `recommendation_agent.py:173`); rag invoked only when `precedent_query is not None` and the workflow passes it through from initial state (`loan_assessment.py:329,395`); `services/knowledge_service/dify_adapter.py`.

**Root cause:** queries are fixed f-strings composed from workflow parameters, decided at workflow start. The model never formulates or refines a query; failure to find good chunks never triggers a reformulated retry (except the freshness signal, which is plumbed but not acted on).

**Impact:** identical inputs → identical queries → **identical chunks every time** (your area 5's "same document chunks repeatedly retrieved"). `top_k=3` on the two synthesis agents starves them further. Retrieval quality directly caps response diversity and specificity.

**Recommendation (P2):** make query formulation an agent step (or at minimum LLM-generated per case from the extraction record); add one reformulate-and-retry round on `no_confident_match`; raise `top_k` for synthesis agents; act on `needs_fresh_search()` in the Market node.

---

### M-3 · MEDIUM — No sampling/diversity controls; format rigidity compounds sameness

**Where:** all `complete_for_agent` call sites (no `temperature`, `top_p`, etc. ever passed); every prompt ends with "exactly these keys… no other text."

**Impact:** provider-default temperature plus maximal format constraint plus identical prompt skeletons yields near-deterministic, homogeneous output. Appropriate for extraction; wrong for conversational replies and qualitative assessments.

**Recommendation (P2):** set task-appropriate sampling per call site (low for extraction/compliance, moderate for conversation/synthesis); move structured output to native tool/structured-output APIs so prose quality is no longer sacrificed to parseability.

---

### M-4 · MEDIUM — "Collaboration" is unidirectional data flow; parallel agents are mutually invisible

**Where:** `workflows/loan_assessment/loan_assessment.py` fan-out (`compliance_check`/`finance_analysis`/`market_research` run concurrently, join at `risk_synthesis`).

**Root cause/impact:** by design, agents communicate only through typed state, only forward, only conclusions (see H-5). Finance never learns compliance found a violation; Market can't focus its search on the sector risk Finance flagged. No negotiation, no cross-examination, no shared scratchpad. Combined with H-1/H-3, the honest description of the current system is: *one LLM, seven prompt templates, fixed order* — your symptom 6, confirmed.

**Recommendation (P2/P3):** cheapest meaningful step is enriching the joins (H-5). True collaboration patterns (Risk querying Compliance for elaboration; a debate/consensus round before Recommendation) belong after the runtime (H-1) exists.

---

### L-1 · LOW — Per-request construction of `Planner()`/`TieredLLMClient` contradicts the stated design

`chat.py:64` builds both per request; `client.py` docstring says "one instance is constructed at process start… and passed down explicitly." Harmless functionally, but bypasses configured `TierModelConfig` injection.

### L-2 · LOW — LLM client hygiene

`except (Exception, litellm.AuthenticationError)` is a redundant tuple; `model_for_tier` reads `os.environ` on every call (`model_tiers.py:92-96`) instead of resolving at config time; the OpenAI fallback map pins outdated models (`gpt-4o` family) — a silent quality downgrade when the OpenAI path activates.

### L-3 · LOW — Hardcoded certainty and canned clarification text

Converse intent always returns `confidence=1.0` (`planner.py:188,259-263`); the low-confidence clarification is a fixed f-string (`planner.py:277-283`) listing the same three examples every time — another repeated-wording source.

---

## 3. What is already good (do not rebuild)

- **Durable execution:** real Postgres-checkpointed LangGraph graphs with six working `interrupt()` approval gates and careful fan-in handling (`workflows/loan_assessment`, `shared/workflow_engine/checkpointer.py`). This is the hard part of production agent infra, and it works.
- **Tool governance:** single-source permission registry with derived allow-lists (`shared/agent_profiles/profiles.py`), per-tool caller enforcement, timeouts, retries, invocation audit logs (`tools/rag/rag_tool.py`).
- **Provenance:** ledger-verified citations that fail closed (`shared/provenance/ledger.py`), trust-tier and freshness enforcement at the tool boundary.
- **Cost architecture:** model tiering per agent (`shared/llm/model_tiers.py`).
- **Failure policy:** Supervisor retry/circuit-breaker (`services/supervisor_service`) — currently starved of real errors by C-1.

These are the guardrails an agentic system needs. The missing piece is the agent.

---

## 4. Prioritized remediation plan

**P0 — this week (small diffs, outsized effect):**
1. Remove/gate the silent mock fallback (C-1). *~1 hour; restores real model output everywhere.*
2. Pass policy clause text into compliance checks (H-6).
3. Add conversation persistence + pass history to the Planner (C-2).

**P1 — the agentic core (2–4 weeks):**
4. Planner v2: parameter extraction from free text, plan object in state, wired workflow dispatch from chat (C-3, H-2).
5. System prompts/personas for all seven agents from their profiles; reasoning-then-structure output via native tool calling (H-3, part of M-3).
6. Enrich inter-agent contracts with rationale; feed full upstream content to Risk/Recommendation (H-5).
7. Build the `GUIDED` agent runtime for one pilot agent (Market or Compliance), then roll out (H-1).

**P2 — adaptivity and quality (following month):**
8. Rework loops on gate rejection; content-conditional routing (H-4).
9. Reviewer/critic pass for Risk + Recommendation; close the calibration feedback loop (M-1).
10. Agentic retrieval: LLM-formulated queries, reformulate-on-miss, larger top_k, act on freshness (M-2).
11. Sampling parameters per task type (M-3).

**P3 — collaboration (after runtime is stable):**
12. Cross-agent elaboration requests / pre-recommendation consensus round (M-4).

---

## 5. Proposed target architecture

No ground-up redesign is needed — the docs' own Layer-4 runtime is the right target. The shape:

```
Officer message
   │
   ▼
Conversation layer (NEW)                ← persistent thread state (Postgres),
   │  history, pending clarifications,     slot-filling, attachments context
   ▼
Planner v2 (UPGRADED)                   ← extracts parameters from text,
   │  emits a Plan {steps, params,         composes templates, asks targeted
   │  assumptions, open questions}         questions it can hear answers to
   ▼
LangGraph workflow templates (KEEP)     ← checkpointer, interrupts, gates,
   │  + rework edges,                      fan-out/fan-in all stay
   │  + content-conditional routing
   ▼
Agent Runtime (NEW — the GUIDED loop)   ← system prompt from AgentProfile,
   │  model ⇄ tools iteration inside       native tool calls restricted to
   │  allowed_tools, existing              allowed_tools, provenance ledger
   │  permission checks unchanged          recording as today
   ▼
Reviewer pass (NEW, Risk/Recommendation only)
   ▼
Human approval gates (KEEP, unchanged)
```

Design principles to preserve while adding agency:
- **Autonomy widens *how*, never *what*:** the runtime iterates freely, but only within `allowed_tools`, and every human gate stays. The profiles registry was explicitly built for this transition — use it.
- **Structured contracts stay, but carry reasoning:** schemas remain the inter-agent interface; they gain rationale fields rather than being replaced by free text.
- **Determinism where determinism is right:** calculations, sanitization, provenance, trust tiers, and routing *enforcement* stay in code. The model decides; the code constrains.

---

*Audit performed against branch `main` at commit `32504a8`. File/line references are to that revision.*
