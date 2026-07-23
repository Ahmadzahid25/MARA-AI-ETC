« [Review Index](00-review-index.md) | Part 5 of 5 »

# Architecture Review Board — Part 5: MVP Reality Check and Final Architecture Decision Report

## 11. MVP Reality Check

The original [14-roadmap.md](../14-roadmap.md) milestone staging is directionally correct (single-agent proof before multi-agent orchestration, production hardening as its own gate). This board's changes are about **scope per stage**, incorporating Parts 1–4's findings, and about explicitly naming what should be *removed*, not merely reordered.

### 11.1 MVP Version 1 — prove the core loop

**Build:**
- Purpose-built thin officer console (not a forked OpenHands frontend — Part 1 §2.5), consuming the extracted event-stream/sandbox/MCP core (Part 1 §2.5) — not the whole OpenHands tree.
- Document Agent (true agent) + Document Assessment workflow.
- Approval Service with the extraction-confirmation gate.
- Audit Memory, **partitioned from day one** (Finding C1) even though volume doesn't yet require it.
- Single, non-HA Postgres/Redis/MinIO (Part 4 §9 — full HA is premature at this scale).

**Explicitly postpone:** Kubernetes HPA, read replicas, multi-region DR, Qdrant, model-tiering infrastructure beyond picking one sensible default model.

**Remove from original scope:** nothing yet — this stage is unchanged in ambition from the original Milestone 1, only narrower in infrastructure.

### 11.2 MVP Version 2 — full Loan Assessment reasoning core

**Build:**
- Knowledge Service (Dify-backed, **on its own database instance** — Finding C2) + document lifecycle approval.
- Compliance, Finance, Risk, Market, Recommendation Agents (true agents per Part 2's classification).
- Planner, constrained to **bounded template selection only** (Finding A1) — this constraint must exist from Market Agent's introduction onward since it's also what closes Red Team finding #3 (unauthorized tool usage via scope confusion).
- Supervisor implemented as **workflow-engine control logic**, not an agent (Part 2, Finding B1).
- Market Agent's search tool ships **only** with query-sanitization enforcement and network-policy-level egress restriction already built (Finding B3) — this is not an add-later hardening step, it is a precondition for this agent existing in any environment with real applicant data.
- Market-data caching into Knowledge Memory routes through the same approval gate as other knowledge content, or is kept in an explicitly lower-trust retrieval tier (Finding C3).
- Citation verification as a deterministic Tool Runtime check (Finding A2).
- Model-tiering strategy live (Part 4 §10.2) — this is the point call volume makes it matter.

**Explicitly postpone:** full multi-department row-level security (single-department pilot doesn't need it yet, per Part 4 §9's 1000-officer scale guidance), full HA/DR.

**Remove from original scope:** Report Agent and Presentation Agent as independent full agents — replaced by a single templating service (optionally merged per Part 2 §4.1) that does not require its own confidence/escalation machinery; Voice Agent as a full agent — replaced by directly-invoked TTS/STT tools; Audit Agent as a full agent for the general case — replaced by a query service, with narrative generation as a thin, clearly-labeled add-on only if a real use case demands it by this point.

### 11.3 Enterprise Version — production, multi-department scale

**Build:** everything in [13-deployment-architecture.md](../13-deployment-architecture.md)'s HA/DR design (now correctly scoped to this stage, not earlier); row-level security multi-tenancy (Finding D3); Audit Memory archival tier; department-level cost governance (Part 4 §10); model/vendor change-control process (Part 4 §8.5); completed third-party security assessment including the prompt-injection and PII-leakage scenarios in Part 3; government compliance sign-off with jurisdiction/data-processing-agreement gates resolved (Findings D1, D2) — not deferred further.

**This is also the earliest point** at which [16-future-expansion.md](../16-future-expansion.md)'s items become appropriate to schedule — the original plan's own sequencing principle here (§16.10) is correct and this board endorses it unchanged.

---

## 12. Final Architecture Decision Report

### 12.1 Architecture Decision Summary

| Decision | Reason | Alternative considered | Why rejected | Residual risk |
|---|---|---|---|---|
| **Narrow the OpenHands reuse to extracted subsystems (event stream, sandbox, MCP, secrets), not a whole-tree fork** | Avoids inheriting a broad-code-execution-by-default security posture and unused coding-agent UI/enterprise surface | Full fork (original plan) | Works against least-privilege by default; frontend UX mismatch not actually cheaper to reskin than to rebuild; harder upstream security-patch merging long-term | Medium — extraction discipline itself takes real engineering care to maintain over time |
| **Keep LangGraph as the workflow engine** | Native fit for durable, checkpointed, multi-day human-approval pauses | Temporal | Higher operational overhead; doesn't natively model LLM/tool-call state | Checkpoint schema versioning across library upgrades (Part 1 §3.1) |
| **Keep CrewAI as inspiration only, not a second orchestrator** | Avoids two components both claiming ownership of retries/state/human-in-the-loop | Run CrewAI's own `Crew`/`Process` as the orchestrator | Direct conflict with LangGraph's checkpointing and audit-trail ownership | Low |
| **Keep Dify as an isolated knowledge service, now on its own database instance** | Reuses mature ingestion/chunking/RAG-admin tooling instead of rebuilding it | Bespoke RAG pipeline | Reinvents a solved problem for no benefit | Low, once DB separation (Finding C2) is implemented |
| **Reclassify 5 of 12 original agents (Supervisor, Report, Presentation, Voice, Audit) as services/workflow nodes** | Matches component design to whether it performs genuine judgment or deterministic transformation; reduces cost, latency, and hallucination surface | Uniform full-agent treatment for all 12 (original plan) | Unjustified LLM-reasoning overhead on components with no real ambiguity to resolve; mislabeling risk (Supervisor built as a prompt-driven component when it should be control code) | Low — this is a simplification, not a capability loss |
| **Single Postgres for all memory kinds at MVP scale, with Audit Memory partitioned from day one** | Transactional consistency and operational simplicity at pilot scale | Separate stores per memory kind from the start | Premature complexity for a component with no proven scale requirement yet | Audit table growth if partitioning is skipped (Finding C1) — mitigated by doing it from day one regardless of current volume |
| **Market Agent remains the sole external-egress tool, now with mandatory query sanitization and network-policy enforcement** | Minimizes exfiltration surface to one auditable, tightly-controlled path | Allow multiple agents controlled egress | Larger attack surface for no functional benefit | PII-in-query leakage if sanitization is skipped (Finding B3) — this is the review's most significant unresolved-in-original-plan risk |
| **Self-hosted-by-default OCR/TTS/STT/LLM path for sensitive data, cloud opt-in gated by classification** | Correct default for a government PII-processing system | Cloud-first with opt-out | Reverses the correct default; cloud provider data-handling terms are a legal/procurement dependency, not a purely technical one | Cross-border jurisdiction not yet specified per concrete provider option (Finding D2) |
| **Human approval gates remain structurally mandatory, not configurable away** | This is the system's core trust proposition and a stated non-negotiable principle | Configurable/optional gates for lower-stakes workflows | Would create a path toward autonomous decisioning by policy drift under throughput pressure (R-B2) | Low — correctly rigid by design; board explicitly endorses keeping this un-softened |
| **Confidence-threshold-driven escalation remains the primary automated trust signal, paired with mandatory calibration tracking** | Enables throughput gains without removing human judgment from genuinely uncertain cases | Pure human review of every output (no confidence gating) | Defeats the throughput goal that is this system's primary business justification | Medium-High — LLM self-reported confidence is not inherently well-calibrated; this is the least mechanically-guaranteed control in the system and requires active, ongoing calibration monitoring, not a set-once threshold |

### 12.2 Required Changes Before Development

**Critical — must be resolved at the design level before Milestone 1 implementation begins:**
1. Commit the Planner to bounded template selection/parameterization only; explicitly forbid free graph topology construction (Finding A1).
2. Add deterministic citation verification at the Tool Runtime, not schema-presence checking alone (Finding A2).
3. Narrow the OpenHands reuse scope to extracted subsystems; do not fork `frontend/` or `enterprise/` wholesale (Part 1 §2.5).
4. Reclassify Supervisor, Report Agent, Presentation Agent, Voice Agent, and (mostly) Audit Agent from full agents to services/workflow nodes before Milestone 1 establishes the agent-build template (Part 2).
5. Resolve the Dify database separation question explicitly — own instance, not implicitly shared with the platform's primary Postgres (Finding C2).
6. Define the model-tiering/routing strategy per agent explicitly (Part 4 §10.2).

**Critical — must be resolved before Milestone 3 (Market Agent introduction) specifically:**
7. Query-sanitization enforcement on the external search tool, verified programmatically, not agent-prompted (Finding B3).
8. Network-policy-level enforcement restricting external egress to the Market Agent's tool pod specifically (Part 3, Red Team #3 mitigation).
9. Market-data caching routed through the same knowledge-lifecycle approval gate as other Knowledge Memory content, or explicitly segregated as a lower-trust retrieval tier agents must treat differently (Finding C3).

**Recommended:**
10. Quarterly access review for tool grants and for Auditor/Administrator role membership, with dual-control on Administrator grants (Part 2 §5.2, Part 3 §7 finding #8).
11. Row-level security in Postgres for branch/department ABAC scoping, not application-layer filtering alone (Finding D3) — required before Enterprise-scale, worth designing for earlier.
12. Notification-delivery reconciliation job distinguishing "awaiting officer attention" from "notification silently failed" (Part 1 §3.3).
13. Circuit breaker at the Supervisor level for systemic LLM/provider degradation (Part 1 §1.3).
14. Named data-processing-agreement/vendor-assessment gate before any cloud-provider opt-in path is enabled (Finding D1), plus explicit per-provider jurisdiction statement (Finding D2).
15. Explicit retry-budget composition rule across tool/agent/workflow retry layers (Part 1 §3.4).
16. Model/vendor change-control process for production LLM swaps (Part 4 §8.5).
17. Explicit search-performance SLO target (Part 3 §6.3).

**Optional:**
18. Merge Report and Presentation services into a single Publishing Service with two renderers (Part 2 §4.1).
19. Replace the placeholder "tested restore drills on a defined cadence" with a concrete quarterly minimum (Part 3 §6.4).
20. Add structural cross-agent consistency checking beyond the Risk Agent's current ad hoc role (Finding A3).

### 12.3 Final Verdict

**Approved with modifications.**

The board is not sending this back for redesign: the foundational shape — layered orchestration/execution/memory/approval separation, tool-permission enforcement independent of agent behavior, human-approval gates that are structurally non-negotiable, audit logging written by independent components, and staged reuse of proven open-source infrastructure rather than reinventing it — is sound and should not be discarded. None of the findings above require abandoning LangGraph, Dify, the OpenHands-derived runtime, or the overall agent/workflow model.

The board is also not approving this unmodified: three findings (Planner graph-construction ambiguity, PII-in-query leakage via the Market Agent, and market-data caching bypassing the knowledge-base approval gate that every other content category requires) are genuine, previously-unaddressed defects in a system designed to process sensitive government and applicant data, and shipping Milestone 1–3 without resolving them would be a real lapse, not a theoretical one. The agent/service reclassification in Part 2 is not optional polish either — building all twelve components as full LLM agents from Milestone 1 onward sets a template the rest of the roadmap would otherwise inherit uncorrected.

**Condition for proceeding:** the seven critical items in §12.2 are resolved at the design/documentation level (updating [03](../03-repository-structure.md), [04](../04-technology-stack.md), [05](../05-agent-architecture.md), [06](../06-tool-architecture.md), and [09](../09-knowledge-architecture.md) as appropriate) before Milestone 1 implementation begins, with items 7–9 specifically gating Milestone 3 rather than blocking earlier work. The recommended and optional items should be scheduled into the roadmap but do not block the start of implementation.

---

« Back to [Review Index](00-review-index.md)
