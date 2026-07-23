« [Review Index](00-review-index.md) | Part 1 of 5 »

# Architecture Review Board — Part 1: Architecture Validation, OpenHands Foundation, Agent Runtime

**Board:** Chief Enterprise Architect, AI Systems Architect, Cloud Architect, Cybersecurity Architect, Data Architect, Government Digital Transformation Advisor, MLOps Engineer, Compliance Officer

**Scope reviewed:** [00-INDEX.md](../00-INDEX.md) through [16-future-expansion.md](../16-future-expansion.md) (the "master plan"), produced prior to this review.

This board does not defer to the master plan's own justifications. Where a decision holds up, we say why. Where it doesn't, we say what breaks and what to do instead.

---

## 1. Architecture Validation

### 1.1 What holds up

- **Layer separation of Planning vs. Supervision vs. Execution** ([02-system-architecture.md](../02-system-architecture.md)) is sound and correctly motivated — these genuinely have different change cadences and different testing needs. Keep it.
- **Centralizing tool execution behind one Tool Runtime with permission checks independent of agent/LLM behavior** ([02](../02-system-architecture.md), [06](../06-tool-architecture.md)) is the single strongest decision in the whole plan. It is what makes the "humans always decide" principle mechanically enforceable rather than aspirational. This survives every attack scenario in Section 7 below better than any other control in the design.
- **Audit Memory written independently by three separate components** ([08-memory-architecture.md](../08-memory-architecture.md) §8.2) is correct defense-in-depth thinking and should not be simplified away under implementation time pressure.

### 1.2 Weak decisions and risky assumptions

**Finding A1 — The Planner's "task graph" is architecturally ambiguous, and the ambiguity is load-bearing.**
[07-workflow-architecture.md](../07-workflow-architecture.md) describes the Planner as producing "a task graph" and separately says LangGraph is the execution substrate. LangGraph `StateGraph`s are normally **compiled from code at build time**, with dynamic behavior expressed through conditional edges over a fixed node set — not freely constructed at runtime from LLM output. The master plan never resolves which model it means:

- If the Planner *selects and parameterizes* one of a small set of pre-built, tested, version-controlled graph templates (Document Assessment, Loan Assessment, etc.) — this is safe, auditable, and testable. Each template's shape is known in advance and can be unit-tested.
- If the Planner *freely constructs novel graph topology* per request — this is a materially different and much riskier system: an LLM emitting executable orchestration topology is an unbounded attack surface (a malformed or adversarially-influenced "plan" could skip a mandatory approval node, since the node-skipping check would itself have to be enforced by something outside the LLM's output), and it is very hard to write a meaningful eval suite against infinite possible graph shapes.

**Verdict: the master plan must commit explicitly to the first model — bounded template selection/parameterization, never free graph construction — and this constraint needs to be a stated, tested invariant** (e.g., a Planner output that references a node type or edge not present in the referenced template's declared schema is rejected before it reaches the Supervisor, not merely discouraged by prompting). As written, [05-agent-architecture.md](../05-agent-architecture.md) §5.2 only says the Planner "propose[s] the graph," which reads as free construction. This is a **required change**, not a nice-to-have — see Part 5.

**Finding A2 — "Every agent" is asserted to write a provenance block, but nothing stops a *fabricated* citation.**
[05-agent-architecture.md](../05-agent-architecture.md) and [06-tool-architecture.md](../06-tool-architecture.md) enforce that a citation *field* is present via output schema validation. Schema validation confirms a citation-shaped string exists; it does not confirm the cited document ID/page/chunk actually appeared in that agent's retrieved tool output. An LLM under normal failure modes fabricates plausible-looking citations (a real document ID, wrong page; or a page number that doesn't contain the claimed figure) far more often than it omits a citation outright — omission is the easy case the current design already handles well, fabrication is the hard case it doesn't handle at all. **This is a gap, not a nuance**: a fabricated-but-well-formed citation is strictly more dangerous than a missing one, because it reads as more trustworthy to the reviewing officer.

**Verdict: add a deterministic citation-verification step** — after an agent emits output, the Tool Runtime (not the agent) cross-checks every cited chunk/document ID against the actual set of tool-call results returned during that task, and rejects/flags any citation that doesn't match. This is cheap (a set-membership check, not another LLM call) and closes a real hole.

**Finding A3 — No component owns cross-agent consistency checking beyond the Risk Agent's ad hoc "material disagreement" escalation.**
[05-agent-architecture.md](../05-agent-architecture.md) §5.7 gives the Risk Agent responsibility for noticing when, e.g., Finance and Compliance disagree — but this is one agent's prompt-level judgment call, not a structural check. There's no equivalent for simpler cross-agent contradictions elsewhere in the graph (e.g., Document Agent extracts a business registration date that Market Agent's sourced context contradicts). This is acceptable to defer, but should be named explicitly as a known gap rather than left implicit — see Finding A3 in Part 5's required-changes list.

### 1.3 Missing architecture pattern: no circuit breaker between layers

The plan has retries (tool-level, [06](../06-tool-architecture.md)) and budgets (per-workflow, [06](../06-tool-architecture.md) §6.4) but no explicit **circuit breaker** pattern for a systemically failing dependency (e.g., the LLM provider is degraded and every agent call is timing out). Without one, a provider outage manifests as every in-flight workflow individually retrying and individually escalating, rather than the platform detecting "the LLM provider is down" once and pausing new dispatch system-wide. Recommend adding this at the Supervisor level — this is a small addition with a large operational payoff, appropriate for Milestone 4 or 6.

---

## 2. OpenHands Foundation Review

The master plan's Phase 4 verdict was "Fork & customize — reuse directly." This board pushes back on the *scope* of that fork, not the underlying premise of reusing OpenHands' proven infrastructure.

### 2.1 Frontend customization difficulty — real concern

OpenHands' frontend is built around a coding-agent UX: file tree, terminal/shell view, browser preview, single-conversation-at-a-time model. MARA AI-ETC's actual UI needs — a multi-workflow Review & Approval Console with document-and-citation side-by-side evidence display, a portfolio Dashboard, role-scoped Admin Console — share almost no component surface with that UX. [04-technology-stack.md](../04-technology-stack.md) §4.2 already conceded LibreChat should be inspiration-only rather than a second frontend "to avoid maintaining two event models" — but that same argument, followed honestly, argues against forking the *OpenHands* frontend too: the event-stream client library is worth reusing, the coding-agent UI chrome built on top of it is not. Reskinning a coding-IDE frontend into a compliance-review console is not meaningfully cheaper than building a purpose-built officer frontend against the same backend event-stream API, and carrying forward unused coding-agent UI surface (file tree, terminal) is dead weight and, per §2.3 below, unnecessary attack surface.

### 2.2 Backend extensibility, event architecture, sandbox model — genuinely strong

`app_server/event`, `event_callback`, and `sandbox` are legitimately reusable: the action/observation event stream is a good structural fit for "agent does something, tool executes, result comes back, log it," and the sandbox gives isolated execution for free. `app_server/mcp` as the tool extension point is a strong, board-endorsed decision — do not replace it with a bespoke plugin system.

### 2.3 Security implications of forking the whole tree — the board's central objection

OpenHands' sandbox is designed to give a coding agent broad shell/code execution capability — that is the product it's built for. MARA AI-ETC's agents need the *opposite* default posture: narrow, per-agent, per-tool allow-lists with no general code execution for agents like Compliance or Recommendation. Forking the entire `app_server` tree means MARA inherits general-purpose code-execution capability as the default and must actively strip it down per agent — security-by-subtraction, which is a worse starting posture than security-by-addition (grant only what's declared, nothing exists until granted). The plan's own permission model ([06-tool-architecture.md](../06-tool-architecture.md)) is addition-based and correct; the substrate underneath it is subtraction-based and works against it. Additionally, `enterprise/` (billing, coding-specific SaaS features) has no role in this system at all and should not be carried forward — every unused module is attack surface and patch-maintenance burden with zero offsetting benefit.

### 2.4 Long-term maintainability

Pulling upstream OpenHands security patches into a customized fork is easiest when the customization footprint is small and clearly separated (extension via `agents/`, `tools/mcp_servers/`, config) and hardest when core `app_server` behavior itself has been rewritten to strip capabilities. A narrow-extraction approach keeps upstream-merge cost low indefinitely; a whole-tree fork with safety-relevant core changes makes every future upstream security patch a manual conflict-resolution exercise against MARA's own safety modifications — exactly the files where a merge mistake is most dangerous.

### 2.5 Board answer

**B — Extract certain components, not a full fork of the tree.**

Concretely: reuse `app_server/event`, `event_callback`, `sandbox`, `mcp`, `secrets` as a vendored/extracted dependency boundary (own package, tracked upstream version, minimal modification footprint) powering the Agent/Tool Runtime. Do **not** fork `frontend/` wholesale — build a purpose-built officer frontend consuming the same event-stream API, borrowing only specific proven interaction patterns (the confirmation-mode approval UI is worth studying closely, per [10-human-in-the-loop.md](../10-human-in-the-loop.md)). Do **not** carry forward `enterprise/`. This changes [03-repository-structure.md](../03-repository-structure.md) and [04-technology-stack.md](../04-technology-stack.md) — flagged as a required change in Part 5.

---

## 3. Agent Runtime Review (LangGraph)

### 3.1 State management and durability — sound, with one caveat

Postgres-backed checkpointing for multi-day human-approval pauses ([07-workflow-architecture.md](../07-workflow-architecture.md), [13-deployment-architecture.md](../13-deployment-architecture.md)) is the right call and was already correctly flagged as the tightest-RPO component (R-T3 in [15-risk-assessment.md](../15-risk-assessment.md)). The caveat: **checkpoint schema versioning across LangGraph library upgrades is a real, underestimated operational hazard**, not just a generic "test it" risk. A LangGraph version bump that changes internal checkpoint serialization can strand in-flight, multi-day-paused workflows in a way that's only discovered when someone tries to resume one. Recommend: pin LangGraph's checkpoint schema version explicitly, and make "can every currently-paused workflow in staging resume after this dependency bump" a named, automated pre-deploy gate — not folded generically into "staging always tests a checkpoint-resume scenario" as currently written.

### 3.2 Multi-agent coordination — the Supervisor's actual job is smaller than "agent" implies

See Finding B1 in Part 2 (Agent Design Review) — the Supervisor as specified is almost entirely deterministic control logic (dispatch, budget enforcement, retry-vs-escalate policy) with no clear case where it needs its own LLM reasoning loop. Calling it an "agent" on par with Document or Finance Agent invites building it with unnecessary LLM-loop machinery (its own prompt, its own confidence threshold, its own escalation target) when it should mostly be deterministic orchestration code implemented as LangGraph control flow itself, with a human-escalation call as a function, not an agent turn.

### 3.3 Human approval pauses — correctly designed, under-specified on notification reliability

The pause/resume mechanism is sound. What's missing: what happens if the notification that a workflow is waiting for approval fails to reach the officer (email delivery failure, notification service outage)? The workflow correctly stays paused (no silent progression — good), but nothing in [10-human-in-the-loop.md](../10-human-in-the-loop.md) or [12-observability.md](../12-observability.md) specifies a **reconciliation job** that periodically scans for approvals pending beyond expected SLA with no confirmed notification delivery and re-notifies or escalates through a secondary channel. Without this, a silently-failed notification and a workflow genuinely awaiting slow officer attention are indistinguishable on the Dashboard — both just show "pending." Recommend adding notification-delivery confirmation as a tracked state, distinct from approval-decision state.

### 3.4 Failure recovery and retry strategy — reasonable layering, one inconsistency

Three independent retry layers exist (tool-level, [06](../06-tool-architecture.md); agent-level escalation, [05](../05-agent-architecture.md); workflow-level blocked-state, [07](../07-workflow-architecture.md) §7.5). This layering is correct in principle but the master plan never states **retry budget composition** — does a tool's 2 retries count against the agent's own retry budget, or are they fully independent? As written, a single failing tool call could consume 2 tool-retries × 2 Supervisor-retries = 4 actual attempts before escalation, which may be fine or may be an unnecessary latency/cost multiplier depending on intent — this needs to be an explicit, stated composition rule, not left to whichever engineer implements it first to decide implicitly.

### 3.5 Long-running tasks — bottleneck risk

**Finding A4 — Sandbox pool contention during OCR-heavy batch periods was already named as R-SC3, correctly, but the mitigation ("scaled independently") is necessary and not sufficient.** OCR jobs are the one tool category most likely to arrive in bursts (a batch of applications submitted at month-end, e.g.). Horizontal scaling of the sandbox pool addresses steady-state throughput but not burst absorption — recommend an explicit queue-and-backpressure design in front of the OCR tool specifically (already implied by Redis/Celery for "ancillary async jobs" per [04-technology-stack.md](../04-technology-stack.md), but OCR is core-path, not ancillary, and its queuing behavior under burst load deserves its own load-test scenario in Milestone 6, not just generic load testing).

---

Continue to Part 2: [Agent Design and Tool Architecture Review](02-agent-and-tool-review.md)
