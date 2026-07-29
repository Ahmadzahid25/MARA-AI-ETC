"""Recommendation Agent — docs/architecture/05-agent-architecture.md §5.8.

    Responsibilities: synthesize all upstream agent outputs into a draft
    recommendation (approve/decline/approve-with-conditions) for officer
    consideration
    Confidence threshold: 0.8
    Model tier: Opus-class — "the one agent where Opus-class (if used at
    all) is cost-justified — lowest call volume, highest stakes"

Two escalation rules used to conflict and are now resolved by an explicit
exception path:

- "Escalates (declines to recommend) if any upstream agent flagged a hard
  compliance violation, **or** if overall confidence is below threshold."
- "Confidence threshold: 0.8; below this, output is explicitly labeled
  'low-confidence — manual assessment recommended' **rather than
  suppressed**."

A hard compliance violation withholds a decision entirely unless the
workflow has recorded an explicit compliance acknowledgment at the gate.
When that acknowledgment exists, this agent proceeds and marks the output
with ``has_acknowledged_violation=True`` for downstream officer visibility.
A merely low-confidence recommendation is **not** withheld:
it still carries a ``decision``, labeled via
``RecommendationOutput.is_low_confidence()``, because "rather than
suppressed" only makes sense if a decision is actually present for the
officer to see and weigh — and this agent's output is always officer-
reviewed regardless of confidence (§5.8: "Always requires explicit officer
approval"), so the label, not suppression, is what the always-mandatory
review gate is for.

Per §5.8's failure handling, a missing upstream input withholds the
recommendation ("recommendation withheld pending [X]"), never computed on
a partial picture — the same pattern `agents/risk_agent` uses for its own
``INCOMPLETE`` status.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from services.knowledge_service.contract import KnowledgeBackend
from shared.agent_profiles import confidence_threshold_for, profile_for
from shared.llm.client import TieredLLMClient
from shared.llm.model_tiers import AgentName
from shared.provenance import ProvenanceLedger
from shared.schemas.compliance import ComplianceChecklist
from shared.schemas.finance import FinancialAnalysis
from shared.schemas.knowledge import (
    DocumentKind,
    PolicyCitation,
    RetrievalFilters,
    RetrievalQuery,
)
from shared.schemas.market import MarketBrief
from shared.schemas.recommendation import RecommendationDecision, RecommendationOutput
from shared.schemas.risk import RiskRating, RiskStatus
from tools.rag.rag_tool import rag_query

PROFILE = profile_for(AgentName.RECOMMENDATION.value)
# Sourced from the profile registry — see shared/agent_profiles/profiles.py.
CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.RECOMMENDATION.value)


class RecommendationParsingError(Exception):
    """The synthesis step (LLM or injected recommender) returned output
    that doesn't match the required shape — surfaced, never silently
    defaulted to a guessed decision."""


class DraftRecommendation:
    """The recommender's raw output, before this agent attaches precedent
    citations and enforces the withholding rules above."""

    __slots__ = ('decision', 'reasoning_trail', 'conditions', 'confidence')

    def __init__(
        self,
        decision: RecommendationDecision,
        reasoning_trail: str,
        conditions: list[str],
        confidence: float,
    ) -> None:
        self.decision = decision
        self.reasoning_trail = reasoning_trail
        self.conditions = conditions
        self.confidence = confidence


# (compliance, finance, risk, market) -> a draft decision. Default calls
# the LLM (Opus tier); tests inject a deterministic fake.
Recommender = Callable[
    [ComplianceChecklist, FinancialAnalysis, RiskRating, MarketBrief],
    Awaitable[DraftRecommendation],
]


def _build_recommendation_prompt(
    compliance_checklist: ComplianceChecklist,
    financial_analysis: FinancialAnalysis,
    risk_rating: RiskRating,
    market_brief: MarketBrief,
) -> str:
    return (
        f'Compliance: {len(compliance_checklist.items)} requirement(s) '
        f'checked, hard violation: {compliance_checklist.has_hard_violation}\n'
        f'Financial assessment: {financial_analysis.assessment} '
        f'(confidence {financial_analysis.assessment_confidence})\n'
        f'Risk rating: status={risk_rating.status.value}, '
        f'components={risk_rating.component_scores}, '
        f'overall={risk_rating.overall_score}, '
        f'range={risk_rating.qualitative_range}\n'
        f'Market: {len(market_brief.claims)} claim(s), '
        f'live_search_available={market_brief.live_search_available}\n\n'
        f'Draft a recommendation. Respond with a JSON object with exactly '
        f'these keys: "decision" (one of "approve", "decline", '
        f'"approve_with_conditions"), "reasoning_trail" (string), '
        f'"conditions" (array of strings, empty unless decision is '
        f'"approve_with_conditions"), "confidence" (float 0.0-1.0). '
        f'Respond with the JSON object only, no other text.'
    )


def _parse_draft(raw_content: str) -> DraftRecommendation:
    try:
        raw = json.loads(raw_content)
        decision = RecommendationDecision(raw['decision'])
        reasoning_trail = str(raw['reasoning_trail'])
        conditions = [str(c) for c in raw['conditions']]
        confidence = float(raw['confidence'])
    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
        raise RecommendationParsingError(
            f'Malformed recommendation output {raw_content!r}: {exc}'
        ) from exc
    if not 0.0 <= confidence <= 1.0:
        raise RecommendationParsingError(
            f'confidence {confidence} out of range [0.0, 1.0]'
        )
    return DraftRecommendation(decision, reasoning_trail, conditions, confidence)


class RecommendationAgent:
    """Configuration of the (not-yet-built) Agent Runtime for the draft
    recommendation — role/goal/tools/confidence-threshold, per
    docs/architecture/05-agent-architecture.md §5.1."""

    profile = PROFILE
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    allowed_tools = PROFILE.allowed_tools

    def __init__(
        self,
        llm_client: TieredLLMClient | None = None,
        recommender: Recommender | None = None,
        backend: KnowledgeBackend | None = None,
    ) -> None:
        self._llm_client = llm_client or TieredLLMClient()
        self._recommender = recommender
        self._backend = backend

    async def recommend(
        self,
        document_id: str,
        *,
        compliance_checklist: ComplianceChecklist | None,
        has_acknowledged_violation: bool = False,
        financial_analysis: FinancialAnalysis | None,
        risk_rating: RiskRating | None,
        market_brief: MarketBrief | None,
        precedent_query: str | None = None,
        workflow_id: str | None = None,
        rag_top_k: int = 3,
        ledger: ProvenanceLedger | None = None,
        audit_sink=None,
    ) -> RecommendationOutput:
        missing = [
            name
            for name, value in (
                ('compliance', compliance_checklist),
                ('finance', financial_analysis),
                ('risk', risk_rating),
                ('market', market_brief),
            )
            if value is None
        ]
        if missing:
            missing_list = ', '.join(missing)
            return RecommendationOutput(
                document_id=document_id,
                missing_inputs=missing,
                withheld_reason=f'Recommendation withheld pending: {missing_list}',
            )
        assert compliance_checklist is not None
        assert financial_analysis is not None
        assert risk_rating is not None
        assert market_brief is not None

        if compliance_checklist.has_hard_violation and not has_acknowledged_violation:
            return RecommendationOutput(
                document_id=document_id,
                withheld_reason=(
                    'A hard compliance violation is present — this agent '
                    'declines to suggest an outcome rather than recommend '
                    'over an unresolved violation '
                    '(docs/architecture/05-agent-architecture.md §5.8)'
                ),
            )

        if risk_rating.status != RiskStatus.COMPLETE:
            return RecommendationOutput(
                document_id=document_id,
                withheld_reason=(
                    f'Risk rating is {risk_rating.status.value}, not '
                    'complete — a recommendation cannot synthesize an '
                    'incomplete or escalated risk picture'
                ),
            )

        if self._recommender is not None:
            draft = await self._recommender(
                compliance_checklist, financial_analysis, risk_rating, market_brief
            )
        else:
            draft = await self._default_recommender(
                compliance_checklist, financial_analysis, risk_rating, market_brief
            )

        precedent_citations: list[PolicyCitation] = []
        if precedent_query is not None:
            result = await rag_query(
                RetrievalQuery(
                    query=precedent_query,
                    top_k=rag_top_k,
                    filters=RetrievalFilters(
                        document_kinds=frozenset({DocumentKind.PRECEDENT})
                    ),
                ),
                caller_agent=AgentName.RECOMMENDATION.value,
                workflow_id=workflow_id,
                backend=self._backend,
                ledger=ledger,
                audit_sink=audit_sink,
            )
            if not result.no_confident_match:
                precedent_citations = [
                    PolicyCitation.from_chunk(chunk) for chunk in result.chunks
                ]
            if ledger is not None:
                ledger.require_verified(
                    tuple(c.to_citable_ref() for c in precedent_citations)
                )

        return RecommendationOutput(
            document_id=document_id,
            decision=draft.decision,
            reasoning_trail=draft.reasoning_trail,
            conditions=draft.conditions,
            confidence=draft.confidence,
            precedent_citations=precedent_citations,
            has_acknowledged_violation=(
                compliance_checklist.has_hard_violation
                and has_acknowledged_violation
            ),
        )

    async def _default_recommender(
        self,
        compliance_checklist: ComplianceChecklist,
        financial_analysis: FinancialAnalysis,
        risk_rating: RiskRating,
        market_brief: MarketBrief,
    ) -> DraftRecommendation:
        prompt = _build_recommendation_prompt(
            compliance_checklist, financial_analysis, risk_rating, market_brief
        )
        response = await self._llm_client.complete_for_agent(
            AgentName.RECOMMENDATION, [{'role': 'user', 'content': prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            raise RecommendationParsingError('Model returned no content')
        return _parse_draft(content)
