# Risk Agent

Implemented (Milestone 3): `RiskAgent.synthesize()` — combines Compliance/
Finance/Market outputs into a risk rating. Component risk-score assignment
(financial/compliance/market, each 0.0-1.0) is the genuinely agentic,
cross-evidence-judgment step (Sonnet-tier LLM call, injectable `assessor`
for tests, per §5.14's agent-vs-service test); combining those three scores
into one overall figure is deterministic and reuses
`tools.calculations`'s `composite_risk_score` formula (0.4/0.4/0.2
weighting) rather than LLM arithmetic.

Real failure/escalation handling, both exercised in
`tests/unit/mara/test_risk_agent.py`:
- Any missing upstream input (Compliance/Finance/Market) yields a
  `RiskStatus.INCOMPLETE` rating naming what's missing, never a rating
  computed on a partial picture.
- §5.6's documented disagreement example — a hard compliance violation
  alongside financials the assessor scored low-risk — yields
  `RiskStatus.ESCALATED` rather than auto-resolving. This is a narrow,
  literal implementation of that one documented example, not an invented
  general "disagreement score" (the architecture doesn't specify one, and
  fabricating a general metric here would be an unreviewed business-logic
  decision this repo's discipline avoids).
- Below the 0.8 confidence threshold, the rating carries a
  `qualitative_range` (`low` / `low-to-moderate` / `moderate-to-high` /
  `high`) instead of a single `overall_score`.

Precedent/risk-policy citations are a real RAG query
(`tools/rag`) against the Milestone-2 Knowledge Service boundary
(`services.knowledge_service.contract.KnowledgeBackend`), scoped to
`DocumentKind.PRECEDENT` and `DocumentKind.POLICY` — `shared/schemas/
knowledge.py` has no dedicated `risk_policy` corpus kind, so this queries
the two closest existing kinds rather than inventing a new taxonomy value
on a shared enum. Citations are `PolicyCitation`, verified against the
task's `ProvenanceLedger` when one is supplied (§6.1), the same as
Compliance/Finance.

See [05-agent-architecture.md#56-risk-agent](../../docs/architecture/05-agent-architecture.md#56-risk-agent)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
