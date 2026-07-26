# Recommendation Agent

Implemented (Milestone 4): `RecommendationAgent.recommend()` — synthesizes
Compliance/Finance/Risk/Market into a draft recommendation
(`RecommendationOutput`), Opus-tier per §5.8's model-tier note. Precedent
citations are a real RAG query against the Knowledge Service boundary
(`DocumentKind.PRECEDENT`), verified against the task's `ProvenanceLedger`
when one is supplied.

Real withholding logic, exercised in
`tests/unit/mara/test_recommendation_agent.py`:
- Any missing upstream input withholds with the specific names ("pending
  compliance, finance"), never computed on a partial picture.
- A hard compliance violation always withholds.
- A risk rating that isn't `RiskStatus.COMPLETE` (incomplete or escalated)
  always withholds — a recommendation cannot synthesize a picture Risk
  itself declined to finish.
- Below the 0.8 confidence threshold, the recommendation is **not**
  withheld — it still carries a `decision`, labeled via
  `RecommendationOutput.is_low_confidence()`. See this module's own
  docstring for why: §5.8's two escalation statements read as
  contradictory ("declines to recommend... if confidence is below
  threshold" vs. "labeled... rather than suppressed") and are resolved
  here deliberately rather than picking one silently.

See [05-agent-architecture.md#58-recommendation-agent](../../docs/architecture/05-agent-architecture.md#58-recommendation-agent)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
