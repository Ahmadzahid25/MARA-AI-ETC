« [Review Index](00-review-index.md) | Part 2 of 5 »

# Architecture Review Board — Part 2: Agent Design and Tool Architecture Review

## 4. Agent Design Review

The original plan proposes 12 agents, each built on the same full Agent Runtime (LLM reasoning loop, its own confidence threshold, its own escalation policy). The board's core finding: **that uniform treatment is itself a design smell.** Not every one of these twelve does work that requires an LLM decision loop, and giving each one the full agent apparatus regardless adds cost, latency, and hallucination surface where a deterministic service would be strictly better *and* strictly more auditable (deterministic code either produces the right output or throws a typed error — it doesn't have a confidence score to miscalibrate).

The test the board applied to each: *does this component make a judgment call that genuinely requires weighing ambiguous or conflicting evidence, or does it execute a well-defined transformation of already-decided input?* The former is an agent. The latter is a service or workflow node.

| Component | Board verdict | Reasoning |
|---|---|---|
| **Planner** | **Keep as agent** — with a constraint | Objective decomposition and workflow-template selection under an ambiguous natural-language request is genuine judgment. Constraint: must select/parameterize from a bounded, versioned template set (Finding A1, Part 1) — not freely construct graph topology. |
| **Supervisor** | **Reclassify as workflow-engine control logic, not an agent** | Dispatch, budget enforcement, and retry-vs-escalate decisions as specified in [05-agent-architecture.md](../05-agent-architecture.md) §5.3 are deterministic policy evaluation, not ambiguous judgment. Implement as LangGraph control-flow code. Keep the *name* "Supervisor" for continuity in documentation/UI if useful, but do not build it with an LLM reasoning loop, its own prompt, or its own confidence threshold — none of those concepts apply to what it actually does. If a genuinely ambiguous supervisory judgment call is later found in practice, add a narrowly-scoped LLM call for that specific decision point, not a general-purpose agent wrapper. |
| **Document Agent** | **Keep as agent** | Classifying document type, choosing extraction strategy per type, and judging extraction confidence is real, variable-input reasoning. Correctly scoped. |
| **Compliance Agent** | **Keep as agent** | Policy interpretation against extracted facts is genuine judgment; no objection. |
| **Finance Agent** | **Keep as agent, with the arithmetic boundary already correctly drawn** | The plan already correctly forces raw calculation through deterministic tools ([06-tool-architecture.md](../06-tool-architecture.md)) and reserves LLM reasoning for interpreting results. This is the right split — no change needed. |
| **Risk Agent** | **Keep as agent** | Synthesis across conflicting evidence is the clearest possible case for genuine agent judgment in this system. |
| **Market Agent** | **Keep as agent, but see Finding B3 (PII-in-query leakage) in Part 3** | Query formulation and source-credibility judgment are real reasoning tasks. Security concern is separate from the agent/service classification question. |
| **Recommendation Agent** | **Keep as agent** | This is the highest-value reasoning component in the system; correctly scoped and correctly gated by mandatory human approval. |
| **Report Agent** | **Downgrade to workflow node / templating service** | As specified, this agent only assembles already-approved content into a document — no new judgment is introduced or permitted ([05-agent-architecture.md](../05-agent-architecture.md) §5.10 explicitly forbids it from including unapproved claims). That is a deterministic assembly job. If narrative smoothing between sections is wanted, scope it as one constrained, template-bounded LLM call inside the service function — not a full agentic tool-loop with its own confidence/escalation machinery it has no real use for. |
| **Presentation Agent** | **Downgrade to workflow node / templating service** | Same reasoning as Report Agent — derivative, content-locked formatting of already-approved material. |
| **Voice Agent** | **Downgrade to a tool pair (TTS/STT), not an agent** | There is no decomposition or judgment happening — TTS is a rendering call, STT is a transcription call with a model-native confidence score. Wrapping this in a full agent adds an unneeded LLM-reasoning layer around what are already just two tools from [06-tool-architecture.md](../06-tool-architecture.md). Keep the STT confidence-gating logic ([05-agent-architecture.md](../05-agent-architecture.md) §5.12) but implement it as a thin service check, not an agent turn. |
| **Audit Agent** | **Split: mostly a query service, thin agent layer only for narrative summarization** | Structured audit queries (what happened, when, by whom) are exactly served by a deterministic query API against Audit Memory — no LLM needed, and no LLM should be in the loop for anything that has to be evidentiary-grade accurate. Reserve an actual LLM-driven "agent" narrowly for the specific, genuinely useful case of producing a readable prose narrative *from* already-correct structured query results, clearly labeled as a generated summary of the authoritative record below it, never as the record itself. |

**Net effect of this reclassification:** the system has roughly **7 true agents** (Planner, Document, Compliance, Finance, Risk, Market, Recommendation) and **5 services/workflow nodes** (Supervisor-as-control-flow, Report, Presentation, Voice-tools, Audit-query-service-plus-thin-narrative-agent). This is a materially leaner, cheaper, more auditable system than "12 agents," and it does not lose any capability described in the original plan — it just implements roughly 40% of them as what they actually are. This reclassification is a **required change** before Milestone 1 begins, because Milestone 1 builds the Document Agent as the template for every agent that follows — if that template over-generalizes the agent pattern, every subsequent milestone inherits the over-generalization.

### 4.1 Should any of these be merged?

Report Agent and Presentation Agent, once both are reclassified as templating services consuming the same approved-content input, are strong merge candidates — a single "Publishing Service" with two output-format renderers (`render_docx`, `render_pptx`) is simpler than two components claiming separate identity for what is fundamentally one job (turn approved content into a distributable artifact). Recommend merging in [03-repository-structure.md](../03-repository-structure.md) and [06-tool-architecture.md](../06-tool-architecture.md) — this is a "recommended," not "critical," change (Part 5).

---

## 5. Tool Architecture Review

### 5.1 MCP servers and tool registry — sound

The MCP-as-extension-point decision is correct and is the review board's preferred outcome for extensibility (endorsed in Part 1 §2.2). No objection to the registry/catalogue approach in [06-tool-architecture.md](../06-tool-architecture.md) §6.2.

### 5.2 Permission system — correct in principle, one gap

The allow-list-per-agent-role model, enforced at the Tool Runtime independent of LLM behavior, is the single best control in the whole architecture (Part 1 §1.1). The gap: **the plan does not specify how a permission grant itself is reviewed or rotated.** `agents/*` config declares tool grants as static configuration ([11-security-architecture.md](../11-security-architecture.md) §11.6), which is good — but nothing describes a periodic access review (who last reviewed that the Finance Agent's tool grants are still minimal-necessary, and when) analogous to standard enterprise IAM access-recertification practice. Recommend adding a quarterly tool-grant review to the operational runbooks (Phase 12/13), tracked as a **recommended** change.

### 5.3 External communication restrictions — correct design, incomplete enforcement surface

Restricting outbound internet access to the Market Agent's search tool alone ([06-tool-architecture.md](../06-tool-architecture.md), [11-security-architecture.md](../11-security-architecture.md) §11.7/§11.9) is right in principle. Two gaps:

1. **Finding B2 — no other agent should ever need external data, but the architecture doesn't structurally prevent a future tool addition from quietly adding a second egress path.** Recommend a network-policy-level control (Phase 13's K8s network policies) that enforces "only the Market Agent's tool pod may reach non-cluster-internal addresses" at the infrastructure layer, not just as a Tool Runtime permission convention — infrastructure-level enforcement survives a future engineer's mistake in a way that application-level convention alone does not.
2. **Finding B3 — PII-in-query leakage.** Restricting *which tool* can reach the internet says nothing about *what data that tool sends externally*. A Market Agent constructing a search query using the applicant's actual business name, owner's name, or other identifying detail leaks PII to an external search provider even though the "only one tool has egress" rule is fully respected — the rule constrains the door, not what walks through it. This is a real, currently-unaddressed data leakage vector. **Recommend: a query-sanitization step, enforced by the tool itself (not agent-trusted), that strips or generalizes personally-identifying detail from search queries before they leave the platform** (e.g., search on sector/industry/region terms, not on the specific applicant's name or IC number) — this is a **critical** finding, escalated in Part 5.

### 5.4 Database access — correct

Parameterized query templates rather than raw agent-generated SQL ([06-tool-architecture.md](../06-tool-architecture.md)) correctly closes the SQL-injection-via-prompt-injection path. No objection.

### 5.5 Document processing and report generation — see agent reclassification above

No new tool-level objection beyond the Section 4 reclassification of Report/Presentation from agents to services, which simplifies rather than complicates this tool category.

### 5.6 Security risks, permission problems, data leakage — summary carried into Part 3

Finding B3 (PII-in-query leakage) is the most significant tool-level finding from this section and is carried forward into the Red Team analysis in Part 3, where its attack-scenario framing belongs.

---

Continue to Part 3: [Data Architecture and Security Red Team Review](03-data-and-security-review.md)
