# MARA AI-ETC — Architecture Review Board Report

**Reviewing:** the master plan at [../00-INDEX.md](../00-INDEX.md) (Phases 1–16)
**Board:** Chief Enterprise Architect, AI Systems Architect, Cloud Architect, Cybersecurity Architect, Data Architect, Government Digital Transformation Advisor, MLOps Engineer, Compliance Officer
**Mandate:** challenge the architecture before implementation begins. No code was written or modified as part of this review; no phase document in the master plan was edited — this report stands alongside it as an independent critique.

## How to read this

This is not a rewrite of the master plan. It is a critique of it, organized around the twelve review areas requested, ending in a scored decision report. Where the board agrees with a decision, it says so briefly and moves on. Where it disagrees, it names the specific finding, traces it to the specific master-plan section it applies to, and states what should change.

## Contents

| Part | Covers |
|---|---|
| [1 — Architecture, OpenHands Foundation, Agent Runtime](01-architecture-and-foundation-review.md) | Overall architecture validation; whether OpenHands should be fully forked, partially extracted, or partially replaced; LangGraph durability/coordination review |
| [2 — Agent and Tool Architecture](02-agent-and-tool-review.md) | Per-agent verdict on whether each of the 12 proposed agents should really be an agent, a service, or a workflow node; tool permission/egress review |
| [3 — Data Architecture and Security Red Team](03-data-and-security-review.md) | Database/knowledge-store design tensions; an 8-scenario adversarial red team pass against the documented controls |
| [4 — Government Compliance, Scalability, Cost](04-compliance-scale-cost-review.md) | PDPA/data-sovereignty gaps; scaling behavior at 10/100/1000 officers; cost drivers and model-routing recommendation |
| [5 — MVP Reality Check and Final Decision](05-mvp-and-final-decision.md) | Revised MVP v1/v2/Enterprise scope; full decision summary table; required-changes list; final verdict |

## Headline findings (full detail in the linked parts)

1. **Three critical, previously-unaddressed gaps** must be resolved before real applicant data reaches Milestones 1–3: the Planner's task-graph generation model is ambiguous in a way that's safety-relevant (Part 1); the Market Agent's search tool can leak applicant PII in query text even though egress is correctly restricted to one tool (Parts 2–3); and market-data caching into the knowledge base bypasses the same approval gate every other knowledge-base content type requires (Part 3).
2. **The "12 agents" design over-generalizes.** Five of the twelve (Supervisor, Report, Presentation, Voice, and mostly Audit) do deterministic transformation or orchestration work, not ambiguous judgment, and should be built as services/workflow nodes, not full LLM-reasoning agents (Part 2). This is a cost, latency, and hallucination-surface reduction, not a capability loss.
3. **The OpenHands reuse decision should be narrowed**, not reversed: extract the event-stream/sandbox/MCP/secrets subsystems, but do not fork the coding-agent-oriented frontend or the unrelated enterprise billing module (Part 1).
4. **The core trust architecture — human approval as structurally non-negotiable, tool permissions enforced independent of agent behavior, audit logging written by independent components — is sound and is explicitly endorsed, not just tolerated** (Parts 1, 3, 5).

## Final verdict

**Approved with modifications.** See [Part 5, §12.3](05-mvp-and-final-decision.md#123-final-verdict) for the full reasoning and the condition attached to it.
