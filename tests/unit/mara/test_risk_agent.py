"""Unit tests for agents/risk_agent/risk_agent.py."""

from __future__ import annotations

import pytest

from agents.risk_agent.risk_agent import ComponentRiskScores, RiskAgent
from shared.schemas.compliance import (
    ComplianceChecklist,
    ComplianceChecklistItem,
    ComplianceStatus,
)
from shared.schemas.finance import FinancialAnalysis
from shared.schemas.knowledge import TrustTier
from shared.schemas.market import MarketBrief
from shared.schemas.risk import RiskStatus


def _passing_checklist() -> ComplianceChecklist:
    return ComplianceChecklist(
        document_id='doc-1',
        items=[
            ComplianceChecklistItem(
                requirement='req-A', status=ComplianceStatus.PASS, notes='ok'
            )
        ],
    )


def _violating_checklist() -> ComplianceChecklist:
    return ComplianceChecklist(
        document_id='doc-1',
        items=[
            ComplianceChecklistItem(
                requirement='req-A', status=ComplianceStatus.FAIL, notes='expired'
            )
        ],
    )


def _finance() -> FinancialAnalysis:
    return FinancialAnalysis(
        document_id='doc-1', figures=[], assessment='ok', assessment_confidence=0.9
    )


def _market() -> MarketBrief:
    return MarketBrief(sector='F&B', region='Klang Valley', claims=[])


async def _fixed_assessor(
    financial_risk, compliance_risk, market_risk, confidence=0.85
):
    async def _assess(checklist, finance, market):
        return ComponentRiskScores(
            financial_risk, compliance_risk, market_risk, confidence
        )

    return _assess


class TestSynthesizeIncomplete:
    @pytest.mark.asyncio
    async def test_missing_all_three_reports_incomplete(self) -> None:
        agent = RiskAgent()
        rating = await agent.synthesize(
            'doc-1',
            compliance_checklist=None,
            financial_analysis=None,
            market_brief=None,
        )
        assert rating.status == RiskStatus.INCOMPLETE
        assert set(rating.missing_inputs) == {'compliance', 'finance', 'market'}

    @pytest.mark.asyncio
    async def test_missing_market_only_reports_incomplete_with_that_name(self) -> None:
        agent = RiskAgent()
        rating = await agent.synthesize(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            market_brief=None,
        )
        assert rating.status == RiskStatus.INCOMPLETE
        assert rating.missing_inputs == ['market']


class TestSynthesizeComplete:
    @pytest.mark.asyncio
    async def test_complete_rating_above_confidence_threshold_has_overall_score(
        self,
    ) -> None:
        assessor = await _fixed_assessor(0.2, 0.1, 0.3, confidence=0.9)
        agent = RiskAgent(assessor=assessor)

        rating = await agent.synthesize(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            market_brief=_market(),
        )

        assert rating.status == RiskStatus.COMPLETE
        assert rating.overall_score is not None
        assert rating.qualitative_range is None
        assert rating.overall_score == pytest.approx(0.2 * 0.4 + 0.1 * 0.4 + 0.3 * 0.2)
        assert rating.component_scores == {
            'financial': 0.2,
            'compliance': 0.1,
            'market': 0.3,
        }

    @pytest.mark.asyncio
    async def test_below_confidence_threshold_reports_qualitative_range_not_score(
        self,
    ) -> None:
        assessor = await _fixed_assessor(0.8, 0.7, 0.9, confidence=0.5)
        agent = RiskAgent(assessor=assessor)

        rating = await agent.synthesize(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            market_brief=_market(),
        )

        assert rating.status == RiskStatus.COMPLETE
        assert rating.overall_score is None
        assert rating.qualitative_range == 'high'


class TestEscalation:
    @pytest.mark.asyncio
    async def test_hard_violation_with_strong_financials_escalates(self) -> None:
        assessor = await _fixed_assessor(0.1, 0.9, 0.2, confidence=0.9)
        agent = RiskAgent(assessor=assessor)

        rating = await agent.synthesize(
            'doc-1',
            compliance_checklist=_violating_checklist(),
            financial_analysis=_finance(),
            market_brief=_market(),
        )

        assert rating.status == RiskStatus.ESCALATED
        assert rating.overall_score is None
        assert rating.qualitative_range is None
        assert 'disagree materially' in rating.escalation_reason

    @pytest.mark.asyncio
    async def test_hard_violation_with_also_weak_financials_does_not_escalate(
        self,
    ) -> None:
        assessor = await _fixed_assessor(0.8, 0.9, 0.2, confidence=0.9)
        agent = RiskAgent(assessor=assessor)

        rating = await agent.synthesize(
            'doc-1',
            compliance_checklist=_violating_checklist(),
            financial_analysis=_finance(),
            market_brief=_market(),
        )

        assert rating.status == RiskStatus.COMPLETE


class TestPrecedentCitations:
    @pytest.mark.asyncio
    async def test_precedent_query_attaches_citations(self) -> None:
        from shared.schemas.knowledge import (
            DocumentKind,
            RetrievalResult,
            RetrievedChunk,
            SensitivityClass,
        )

        chunk = RetrievedChunk(
            document_id='precedent-1',
            version='v1',
            locator='4',
            text='Similar case approved with conditions.',
            relevance=0.75,
            document_kind=DocumentKind.PRECEDENT,
            sensitivity=SensitivityClass.INTERNAL,
            trust_tier=TrustTier.APPROVED,
        )

        class StubBackend:
            async def retrieve(self, query):
                assert query.filters.document_kinds == frozenset(
                    {DocumentKind.PRECEDENT, DocumentKind.POLICY}
                )
                return RetrievalResult(chunks=(chunk,))

        assessor = await _fixed_assessor(0.2, 0.1, 0.2, confidence=0.9)
        agent = RiskAgent(assessor=assessor, backend=StubBackend())

        rating = await agent.synthesize(
            'doc-1',
            compliance_checklist=_passing_checklist(),
            financial_analysis=_finance(),
            market_brief=_market(),
            precedent_query='similar F&B loan cases',
        )

        assert len(rating.citations) == 1
        assert rating.citations[0].document_id == 'precedent-1'
