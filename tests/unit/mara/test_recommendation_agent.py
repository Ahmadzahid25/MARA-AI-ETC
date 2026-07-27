"""Unit tests for agents/recommendation_agent/recommendation_agent.py."""

from __future__ import annotations

import pytest

from agents.recommendation_agent.recommendation_agent import (
    DraftRecommendation,
    RecommendationAgent,
)
from shared.schemas.compliance import (
    ComplianceChecklist,
    ComplianceChecklistItem,
    ComplianceStatus,
)
from shared.schemas.finance import FinancialAnalysis
from shared.schemas.knowledge import TrustTier
from shared.schemas.market import MarketBrief
from shared.schemas.recommendation import RecommendationDecision
from shared.schemas.risk import RiskRating, RiskStatus


def _passing_checklist() -> ComplianceChecklist:
    return ComplianceChecklist(
        document_id='doc-1',
        items=[
            ComplianceChecklistItem(requirement='req-A', status=ComplianceStatus.PASS)
        ],
    )


def _violating_checklist() -> ComplianceChecklist:
    return ComplianceChecklist(
        document_id='doc-1',
        items=[
            ComplianceChecklistItem(requirement='req-A', status=ComplianceStatus.FAIL)
        ],
    )


def _finance() -> FinancialAnalysis:
    return FinancialAnalysis(
        document_id='doc-1', assessment='ok', assessment_confidence=0.9
    )


def _complete_risk(confidence: float = 0.9) -> RiskRating:
    return RiskRating(
        document_id='doc-1',
        status=RiskStatus.COMPLETE,
        component_scores={'financial': 0.2, 'compliance': 0.1, 'market': 0.2},
        overall_score=0.18,
        confidence=confidence,
    )


def _incomplete_risk() -> RiskRating:
    return RiskRating(
        document_id='doc-1', status=RiskStatus.INCOMPLETE, missing_inputs=['market']
    )


def _market() -> MarketBrief:
    return MarketBrief(sector='F&B', region='Klang Valley', claims=[])


async def _fixed_recommender(decision, confidence=0.9, conditions=None):
    async def recommender(compliance, finance, risk, market):
        return DraftRecommendation(
            decision=decision,
            reasoning_trail='Solid case.',
            conditions=conditions or [],
            confidence=confidence,
        )

    return recommender


class TestMissingInputs:
    @pytest.mark.asyncio
    async def test_missing_all_withholds_with_names(self) -> None:
        agent = RecommendationAgent()
        output = await agent.recommend(
            'doc-1',
            compliance_checklist=None,
            financial_analysis=None,
            risk_rating=None,
            market_brief=None,
        )

        assert output.decision is None
        assert output.withheld_reason is not None
        assert set(output.missing_inputs) == {'compliance', 'finance', 'risk', 'market'}

    @pytest.mark.asyncio
    async def test_missing_market_only(self) -> None:
        agent = RecommendationAgent()
        output = await agent.recommend(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            risk_rating=_complete_risk(),
            market_brief=None,
        )

        assert output.missing_inputs == ['market']


class TestHardViolationWithholds:
    @pytest.mark.asyncio
    async def test_hard_violation_withholds_regardless_of_recommender(self) -> None:
        recommender = await _fixed_recommender(RecommendationDecision.APPROVE)
        agent = RecommendationAgent(recommender=recommender)

        output = await agent.recommend(
            'doc-1',
            compliance_checklist=_violating_checklist(),
            financial_analysis=_finance(),
            risk_rating=_complete_risk(),
            market_brief=_market(),
        )

        assert output.decision is None
        assert 'hard compliance violation' in output.withheld_reason.lower()


class TestIncompleteRiskWithholds:
    @pytest.mark.asyncio
    async def test_incomplete_risk_withholds(self) -> None:
        recommender = await _fixed_recommender(RecommendationDecision.APPROVE)
        agent = RecommendationAgent(recommender=recommender)

        output = await agent.recommend(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            risk_rating=_incomplete_risk(),
            market_brief=_market(),
        )

        assert output.decision is None
        assert 'not complete' in output.withheld_reason.lower()


class TestNormalRecommendation:
    @pytest.mark.asyncio
    async def test_approve_decision_is_returned(self) -> None:
        recommender = await _fixed_recommender(
            RecommendationDecision.APPROVE, confidence=0.9
        )
        agent = RecommendationAgent(recommender=recommender)

        output = await agent.recommend(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            risk_rating=_complete_risk(),
            market_brief=_market(),
        )

        assert output.decision == RecommendationDecision.APPROVE
        assert output.withheld_reason is None
        assert output.is_low_confidence() is False

    @pytest.mark.asyncio
    async def test_low_confidence_is_not_withheld_but_labeled(self) -> None:
        recommender = await _fixed_recommender(
            RecommendationDecision.APPROVE_WITH_CONDITIONS,
            confidence=0.5,
            conditions=['Provide updated bank statement'],
        )
        agent = RecommendationAgent(recommender=recommender)

        output = await agent.recommend(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            risk_rating=_complete_risk(),
            market_brief=_market(),
        )

        assert output.decision == RecommendationDecision.APPROVE_WITH_CONDITIONS
        assert output.withheld_reason is None
        assert output.is_low_confidence(threshold=0.8) is True

    @pytest.mark.asyncio
    async def test_precedent_query_attaches_citations(self) -> None:
        from shared.schemas.knowledge import (
            DocumentKind,
            RetrievalResult,
            RetrievedChunk,
            SensitivityClass,
        )

        chunk = RetrievedChunk(
            document_id='precedent-2',
            version='v1',
            locator='1',
            text='Similar F&B case, approved.',
            relevance=0.8,
            document_kind=DocumentKind.PRECEDENT,
            sensitivity=SensitivityClass.INTERNAL,
            trust_tier=TrustTier.APPROVED,
        )

        class StubBackend:
            async def retrieve(self, query):
                assert query.filters.document_kinds == frozenset(
                    {DocumentKind.PRECEDENT}
                )
                return RetrievalResult(chunks=(chunk,))

        recommender = await _fixed_recommender(RecommendationDecision.APPROVE)
        agent = RecommendationAgent(recommender=recommender, backend=StubBackend())

        output = await agent.recommend(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            risk_rating=_complete_risk(),
            market_brief=_market(),
            precedent_query='similar F&B cases',
        )

        assert len(output.precedent_citations) == 1
        assert output.precedent_citations[0].document_id == 'precedent-2'
