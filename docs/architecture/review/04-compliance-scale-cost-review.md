« [Review Index](00-review-index.md) | Part 4 of 5 »

# Architecture Review Board — Part 4: Government Compliance, Scalability, and Cost Review

## 8. Government Compliance Review

**A note on scope from the Compliance Officer and Government Digital Transformation Advisor:** this board can evaluate whether the *architecture* creates the technical preconditions for compliance (data residency, access control, audit trails, retention). It cannot certify actual legal/regulatory compliance — that requires MARA's own legal, compliance, and ICT security governance functions, and, for a government system of this sensitivity, an accredited third-party assessment. Anywhere below the board names a specific requirement, treat it as "the architecture must be capable of satisfying this category of requirement," not as a substitute for that formal review.

### 8.1 PDPA Malaysia

The architecture's PDPA posture (data minimization, purpose limitation, self-hosted-by-default sensitive processing, accountability via Audit Memory, correction/erasure paths — [11-security-architecture.md](../11-security-architecture.md) §11.4) is a genuinely above-baseline starting design; most systems bolt this on after the fact, this plan designed for it. Two specific gaps:

- **Finding D1 — no data processing agreement / vendor assessment step is named for any cloud LLM/OCR/TTS provider actually used**, even for the deliberately narrower "non-sensitive" opt-in paths. [11-security-architecture.md](../11-security-architecture.md) §11.7 mentions "contractually bound (zero-retention/no-training-on-input terms) as a prerequisite" but this needs to be a tracked, named gate in the roadmap (currently absent from [14-roadmap.md](../14-roadmap.md)), not a background assumption — a Milestone should not be able to enable a cloud-provider opt-in path without this being explicitly checked off.
- **Finding D2 — cross-border data flow is not explicitly addressed.** Even "self-hosted" infrastructure needs a stated hosting location, and even the LLM provider abstraction (LiteLLM, per [04-technology-stack.md](../04-technology-stack.md)) needs the actual API endpoint's jurisdiction stated per provider option (Anthropic direct API vs. AWS Bedrock in a specific region) — PDPA's cross-border transfer provisions turn on this, and the architecture currently treats "self-hosted vs. cloud" as the only axis when "which jurisdiction" is a second, separate axis that needs its own explicit decision per data-sensitivity tier.

### 8.2 Government ICT security requirements and data sovereignty

The architecture's constraints (self-hostability, Kubernetes/mainstream-tooling operability by MARA's own IT team, avoidance of hard foreign-SaaS dependency — [01-vision.md](../01-vision.md) §1.7) are directionally correct for a government deployment, but the master plan doesn't reference any specific government ICT security framework or accreditation process MARA is actually subject to. This board is not positioned to name the exact applicable framework with confidence — **that determination has to come from MARA's own ICT security governance function**, and the architecture should treat "which specific government security framework/accreditation applies, and what does it specifically require" as an open input to be resolved before Milestone 6's security assessment (Phase 14.8), not an assumption baked into the design already. Recommend this be an explicit, named action item, not left implicit.

### 8.3 Audit requirements and document confidentiality

Well covered structurally (Audit Memory immutability, independent multi-writer audit logging, document classification-driven access control). No material gap beyond what's already flagged in Parts 1–3 (citation verification, RAG-poisoning approval gap).

### 8.4 Access control

RBAC/ABAC design ([11-security-architecture.md](../11-security-architecture.md) §11.2) is sound in principle. **Finding D3 — branch/department-level data isolation (ABAC scoping "officer may only approve applications in their assigned branch") is asserted but not architecturally detailed** — is this enforced via row-level security policies in Postgres, application-layer filtering, or both? For a government system, relying on application-layer filtering alone (rather than database-enforced row-level security as a second, independent layer) repeats exactly the single-layer-of-defense mistake the plan correctly avoided elsewhere (e.g., Tool Runtime permission checks existing independently of agent behavior). Recommend explicit row-level security policies in Postgres as a stated requirement, not just an application-level ABAC check.

### 8.5 Missing governance requirement: model/vendor change control

Nothing in the master plan describes a governance process for *changing* which LLM model or provider an agent uses in production (e.g., swapping Claude Sonnet for a newer model version). For a government decision-support system, a model change can silently shift agent behavior/accuracy — this needs to be a change-controlled, evaluated event (re-run `tests/agent_evals/` regression suite, documented sign-off) not a routine config update. Recommend adding this explicitly to Phase 12's governance/observability scope.

---

## 9. Scalability Review

Evaluated at the three named scale points. The board's central finding here: **the master plan's Phase 13 HA/DR design is correctly specified for the 1000-officer/production endpoint, but nothing in the roadmap states that this is *not* the target for early milestones** — building full multi-replica Postgres HA, Redis Sentinel, and distributed MinIO for a 10-officer pilot is premature investment that slows Milestone 1–3 delivery for no benefit at pilot scale. This connects directly to the MVP discussion in Part 5.

| Scale | Database | Agent concurrency | Queue | LLM cost | Storage growth | Monitoring |
|---|---|---|---|---|---|---|
| **10 officers (pilot)** | Single Postgres instance, no read replica needed. Table partitioning for Audit Memory (Finding C1) should still be done now — it's a schema decision, cheap to do early, expensive to retrofit later, independent of current load. | Low — sequential/small-batch dispatch is fine; HPA autoscaling is unnecessary complexity at this scale. | Single Redis instance, no cluster mode needed. | Dominant cost driver even at this scale is per-workflow LLM call volume (7 real agents × multiple tool-loop turns each), not infrastructure — model-tiering (9.3 below) matters from day one regardless of user count, since it's a per-call not per-user cost. | Negligible. | Basic Prometheus/Grafana sufficient; Langfuse valuable immediately for prompt/eval iteration during this exact phase. |
| **100 officers** | Read replica becomes worthwhile for Dashboard/reporting query load separate from the transactional write path. Audit partitioning now paying off. | HPA scaling of Agent Runtime pods becomes relevant; sandbox pool burst behavior (Finding A4, Part 1) should be load-tested at this scale specifically, since OCR batch bursts scale with officer count. | Redis Sentinel/cluster mode justified. | Now a real budget line — model-tiering strategy (9.3) should be implemented, not deferred, before this scale is reached. | Object storage growth becomes trackable/forecastable; lifecycle policies (Phase 13.5) should be tuned against real data. | SLO-based alerting (Phase 12.9) becomes necessary — at 10 officers, a human notices something's wrong; at 100, they don't without alerting. |
| **1000 officers / multiple departments** | **Finding D3's row-level security becomes load-bearing, not optional**, for genuine multi-tenant data isolation across departments. The single-Postgres-for-everything decision should be actively re-examined here, not assumed to still hold — Knowledge Memory (Finding C2) and Audit Memory (Finding C1) are the most likely candidates to need separation onto dedicated infrastructure by this point. | Full HPA, likely multiple Agent Runtime pools segmented by department/workload class. | Full HA queue infrastructure as specified in Phase 13. | Org-wide cost governance/chargeback per department becomes necessary — the per-workflow/per-branch cost tracking already specified in [12-observability.md](../12-observability.md) §12.7 is the right foundation, extend it to a department-level budget/alert, not just a dashboard. | pgvector-to-Qdrant migration path ([04-technology-stack.md](../04-technology-stack.md) §4.3) is likely triggered around this scale, not before — don't pre-migrate. | Full observability stack as specified in Phase 12 is appropriate at this scale, not before. |

---

## 10. Cost Analysis

The board declines to fabricate specific dollar figures — no committed LLM call volume, document volume, or officer count exists yet to model against, and false-precision cost estimates would mislead budget planning more than they'd help it. Instead: relative cost drivers, ranked, and concrete optimization levers.

### 10.1 Major cost drivers, ranked by expected relative magnitude

1. **LLM token cost** — dominant driver, and scales with *agent call volume × turns per call*, not directly with officer headcount. The 12→7-real-agent reclassification in Part 2 is itself a direct cost reduction: five fewer components running full LLM reasoning loops.
2. **OCR processing** — self-hosted (PaddleOCR/Tesseract) shifts this from a per-call API cost to a compute/infrastructure cost, which is the right call for both data residency and cost predictability at volume — API-metered OCR at MARA's expected document volume would likely be more expensive at scale than owning the compute.
3. **Vector database / embeddings** — embedding generation cost scales with corpus size and re-ingestion frequency; retrieval cost (pgvector, self-hosted) is compute, not per-query billed.
4. **Compute (Kubernetes cluster)** — baseline infrastructure cost, relatively predictable and the smallest lever compared to #1.
5. **Storage** — smallest driver at any scale discussed here; document/artifact volume grows linearly and predictably.
6. **Monitoring/observability stack** — self-hosted (Langfuse, Prometheus/Grafana/Loki per [04-technology-stack.md](../04-technology-stack.md)) keeps this a compute cost, not a per-seat SaaS cost — correct call, avoid any temptation to swap to a metered SaaS observability vendor as the officer count grows, since that would turn a fixed cost into a scaling one for no functional benefit.

### 10.2 Cost optimization strategies

- **Model routing / tiering — the single largest lever, and currently absent from the master plan.** [04-technology-stack.md](../04-technology-stack.md) §4.6 names the Claude Sonnet/Opus/Haiku family as available but does not specify which agent uses which tier. **Recommend, as a required change**: high-call-volume, lower-ambiguity agents (Document classification/extraction) route to the smallest capable tier (Haiku-class); synthesis-heavy agents (Compliance, Finance, Risk, Market) route to a mid tier (Sonnet-class); the Recommendation Agent — lowest call volume, highest stakes — is the one place where the largest tier (Opus-class), if used at all, is actually cost-justified. Without this stated explicitly, the default implementation risk is "use one capable model everywhere," which is the single most expensive way to build this system.
- **Local/open-weight fallback** ([04-technology-stack.md](../04-technology-stack.md) §4.6, vLLM path) is correctly identified as a data-residency lever; it is *also* a cost lever at sufficient volume (fixed compute cost vs. per-token billing crosses over at some volume) and should be evaluated on both dimensions, not data-residency alone.
- **Cost circuit breaker** (Finding A4-adjacent, Part 1 §1.3) doubles as a cost control — a systemically failing/looping agent burns budget fast without one.
- **Confidence-threshold tuning against correction-rate data** ([08-memory-architecture.md](../08-memory-architecture.md), [10-human-in-the-loop.md](../10-human-in-the-loop.md)) is also a cost lever, not just a quality one: an over-cautious threshold that escalates too often burns officer time (a cost) reviewing things that didn't need review, while an under-cautious one burns trust. This tuning loop should be tracked as a cost metric on the Phase 12 dashboard, not only a quality metric.

---

Continue to Part 5: [MVP Reality Check and Final Architecture Decision Report](05-mvp-and-final-decision.md)
