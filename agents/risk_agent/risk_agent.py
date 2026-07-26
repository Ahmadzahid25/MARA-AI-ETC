"""Risk Agent — docs/architecture/05-agent-architecture.md §5.6.

    Responsibilities: synthesize Document/Compliance/Finance/Market outputs
    into a risk profile and risk rating
    Confidence threshold: 0.8
    Model tier: Sonnet-class (synthesis tier)

Two distinct steps, matching §5.14's agent-vs-service test: assigning the
three component risk scores from Compliance/Finance/Market evidence is
genuine, ambiguous cross-evidence judgment (the agentic step, via
``RiskAssessor`` — LLM by default, injectable for tests); combining those
three scores into one overall figure is deterministic and reuses
``tools.calculations``'s ``composite_risk_score`` formula (§5.6: "allowed
tools ... calculation tools for risk-scoring formulas") rather than asking
the LLM to do that arithmetic itself.

Per §5.6's escalation rule, this agent does not auto-resolve a material
disagreement between components — the documented example (strong
financials but a hard compliance flag) is implemented as a concrete,
narrow check rather than an invented general "disagreement score," since
the architecture doesn't specify a general metric and fabricating one here
would be exactly the kind of unreviewed business-judgment call this
repo's discipline avoids.

Precedent/risk-policy lookup goes through the real Milestone-2
``services.knowledge_service.contract.KnowledgeBackend`` /
``tools.rag.rag_tool.rag_query`` boundary, the same one Compliance/
Finance/Market use. §5.6 names two corpora ("historical precedent, risk
policy"); ``shared/schemas/knowledge.py``'s ``DocumentKind`` has no
dedicated ``risk_policy`` member, so this queries both ``PRECEDENT`` and
``POLICY`` rather than inventing a new taxonomy value unilaterally on a
shared enum someone else owns.
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
from shared.schemas.risk import RiskRating, RiskStatus
from tools.calculations.calculation_tool import calculate
from tools.rag.rag_tool import rag_query

PROFILE = profile_for(AgentName.RISK.value)
# Sourced from the profile registry — see shared/agent_profiles/profiles.py.
CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.RISK.value)
# §5.6's own example of a material disagreement: a hard compliance
# violation alongside financials the assessor judged low-risk. Not a
# general "any large gap between components" rule — see module docstring.
STRONG_FINANCIALS_RISK_CEILING = 0.3
PRECEDENT_DOCUMENT_KINDS = frozenset({DocumentKind.PRECEDENT, DocumentKind.POLICY})


class RiskAssessmentParsingError(Exception):
    """The component-scoring step (LLM or injected assessor) returned
    output that doesn't match the required shape — surfaced, never
    silently defaulted to a guessed score."""


class ComponentRiskScores:
    __slots__ = ('financial_risk', 'compliance_risk', 'market_risk', 'confidence')

    def __init__(
        self,
        financial_risk: float,
        compliance_risk: float,
        market_risk: float,
        confidence: float,
    ) -> None:
        self.financial_risk = financial_risk
        self.compliance_risk = compliance_risk
        self.market_risk = market_risk
        self.confidence = confidence


# (compliance checklist, financial analysis, market brief) -> component
# scores. Default calls the LLM (Sonnet tier); tests inject a deterministic
# fake.
RiskAssessor = Callable[
    [ComplianceChecklist, FinancialAnalysis, MarketBrief],
    Awaitable[ComponentRiskScores],
]


def _qualitative_range(score: float) -> str:
    if score < 0.25:
        return 'low'
    if score < 0.5:
        return 'low-to-moderate'
    if score < 0.75:
        return 'moderate-to-high'
    return 'high'


def _build_assessment_prompt(
    compliance_checklist: ComplianceChecklist,
    financial_analysis: FinancialAnalysis,
    market_brief: MarketBrief,
) -> str:
    compliance_text = (
        'HARD VIOLATION PRESENT' if compliance_checklist.has_hard_violation else 'no hard violation'
    )
    figures_text = '\n'.join(
        f'- {f.name}: {f.value} ({f.provenance.value})' for f in financial_analysis.figures
    )
    claims_text = '\n'.join(
        f'- {c.claim} (credibility {c.credibility_score})' for c in market_brief.claims
    )
    return (
        f'Compliance status: {compliance_text}\n\n'
        f'Financial figures:\n{figures_text}\n'
        f'Financial assessment: {financial_analysis.assessment} '
        f'(confidence {financial_analysis.assessment_confidence})\n\n'
        f'Market claims:\n{claims_text}\n\n'
        f'Assign a risk score to each of "financial", "compliance", and '
        f'"market" (0.0 = lowest risk, 1.0 = highest risk), and your '
        f'overall confidence in this assessment. Respond with a JSON '
        f'object with exactly these keys: "financial_risk", '
        f'"compliance_risk", "market_risk", "confidence" (all floats '
        f'0.0-1.0). Respond with the JSON object only, no other text.'
    )


def _parse_assessment(raw_content: str) -> ComponentRiskScores:
    try:
        raw = json.loads(raw_content)
        values = {
            key: float(raw[key])
            for key in ('financial_risk', 'compliance_risk', 'market_risk', 'confidence')
        }
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise RiskAssessmentParsingError(
            f'Malformed risk assessment output {raw_content!r}: {exc}'
        ) from exc
    for key, value in values.items():
        if not 0.0 <= value <= 1.0:
            raise RiskAssessmentParsingError(
                f'{key} {value} out of range [0.0, 1.0]'
            )
    return ComponentRiskScores(**values)


class RiskAgent:
    """Configuration of the (not-yet-built) Agent Runtime for risk
    synthesis — role/goal/tools/confidence-threshold, per docs/architecture/
    05-agent-architecture.md §5.1."""

    profile = PROFILE
    confidence_threshold: float = CONFIDENCE_THRESHOLD
    allowed_tools = PROFILE.allowed_tools

    def __init__(
        self,
        llm_client: TieredLLMClient | None = None,
        assessor: RiskAssessor | None = None,
        backend: KnowledgeBackend | None = None,
    ) -> None:
        self._llm_client = llm_client or TieredLLMClient()
        self._assessor = assessor
        self._backend = backend

    async def synthesize(
        self,
        document_id: str,
        *,
        compliance_checklist: ComplianceChecklist | None,
        financial_analysis: FinancialAnalysis | None,
        market_brief: MarketBrief | None,
        precedent_query: str | None = None,
        workflow_id: str | None = None,
        rag_top_k: int = 3,
        ledger: ProvenanceLedger | None = None,
        audit_sink=None,
    ) -> RiskRating:
        """Synthesize a risk rating from the three upstream agents' output.
        Per §5.6's failure handling, returns an ``INCOMPLETE`` rating
        (never computed on a partial picture) if any of the three is
        ``None``.
        """

        missing = [
            name
            for name, value in (
                ('compliance', compliance_checklist),
                ('finance', financial_analysis),
                ('market', market_brief),
            )
            if value is None
        ]
        if missing:
            return RiskRating(
                document_id=document_id,
                status=RiskStatus.INCOMPLETE,
                missing_inputs=missing,
            )
        assert compliance_checklist is not None
        assert financial_analysis is not None
        assert market_brief is not None

        if self._assessor is not None:
            scores = await self._assessor(
                compliance_checklist, financial_analysis, market_brief
            )
        else:
            scores = await self._default_assessor(
                compliance_checklist, financial_analysis, market_brief
            )

        citations: list[PolicyCitation] = []
        if precedent_query is not None:
            result = await rag_query(
                RetrievalQuery(
                    query=precedent_query,
                    top_k=rag_top_k,
                    filters=RetrievalFilters(document_kinds=PRECEDENT_DOCUMENT_KINDS),
                ),
                caller_agent=AgentName.RISK.value,
                workflow_id=workflow_id,
                backend=self._backend,
                ledger=ledger,
                audit_sink=audit_sink,
            )
            if not result.no_confident_match:
                citations = [
                    PolicyCitation.from_chunk(chunk) for chunk in result.chunks
                ]
            if ledger is not None:
                # §6.1 — see agents/finance_agent/finance_agent.py's identical
                # note: these citations are built directly from what rag_query
                # just returned, so this can never actually reject, but the
                # invariant is enforced the same way everywhere regardless.
                ledger.require_verified(tuple(c.to_citable_ref() for c in citations))

        if (
            compliance_checklist.has_hard_violation
            and scores.financial_risk < STRONG_FINANCIALS_RISK_CEILING
        ):
            return RiskRating(
                document_id=document_id,
                status=RiskStatus.ESCALATED,
                component_scores={
                    'financial': scores.financial_risk,
                    'compliance': scores.compliance_risk,
                    'market': scores.market_risk,
                },
                confidence=scores.confidence,
                citations=citations,
                escalation_reason=(
                    'Compliance hard violation present alongside a low '
                    f'financial risk score ({scores.financial_risk}) — '
                    'components disagree materially; not auto-resolved '
                    '(docs/architecture/05-agent-architecture.md §5.6)'
                ),
            )

        calc_result = calculate(
            'composite_risk_score',
            {
                'financial_risk': scores.financial_risk,
                'compliance_risk': scores.compliance_risk,
                'market_risk': scores.market_risk,
            },
            caller_agent=AgentName.RISK.value,
            workflow_id=workflow_id,
            audit_sink=audit_sink,
        )

        rating = RiskRating(
            document_id=document_id,
            status=RiskStatus.COMPLETE,
            component_scores={
                'financial': scores.financial_risk,
                'compliance': scores.compliance_risk,
                'market': scores.market_risk,
            },
            confidence=scores.confidence,
            citations=citations,
        )
        if scores.confidence < CONFIDENCE_THRESHOLD:
            rating.qualitative_range = _qualitative_range(calc_result.value)
        else:
            rating.overall_score = calc_result.value
        return rating

    async def _default_assessor(
        self,
        compliance_checklist: ComplianceChecklist,
        financial_analysis: FinancialAnalysis,
        market_brief: MarketBrief,
    ) -> ComponentRiskScores:
        prompt = _build_assessment_prompt(
            compliance_checklist, financial_analysis, market_brief
        )
        response = await self._llm_client.complete_for_agent(
            AgentName.RISK, [{'role': 'user', 'content': prompt}]
        )
        content = response.choices[0].message.content
        if content is None:
            raise RiskAssessmentParsingError('Model returned no content')
        return _parse_assessment(content)
