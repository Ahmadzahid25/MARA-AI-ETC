"""Unit tests for workflows/loan_assessment/loan_assessment.py.

Uses a real LangGraph ``InMemorySaver`` checkpointer (not a mock) — the
same approach `tests/unit/mara/test_document_assessment_workflow.py` uses
— to exercise the actual durable-pause/resume mechanics across this
workflow's five approval gates and its Compliance/Finance/Market fan-out.
"""

from __future__ import annotations

import io

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pypdf import PdfWriter

from agents.compliance_agent.compliance_agent import ComplianceAgent
from agents.document_agent.document_agent import DocumentAgent
from agents.finance_agent.finance_agent import FinanceAgent
from agents.market_agent.market_agent import MarketAgent
from agents.recommendation_agent.recommendation_agent import (
    DraftRecommendation,
    RecommendationAgent,
)
from agents.risk_agent.risk_agent import ComponentRiskScores, RiskAgent
from shared.provenance import FabricatedCitationError
from shared.schemas.compliance import ComplianceStatus
from shared.schemas.documents import Citation, ExtractedField, ExtractionSource
from shared.schemas.recommendation import RecommendationDecision
from workflows.loan_assessment.loan_assessment import (
    LoanAssessmentState,
    build_loan_assessment_graph,
)


def _blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


async def _fake_field_extractor(pages, classification) -> list[ExtractedField]:
    return [
        ExtractedField(
            name='applicant_name',
            value='Ali bin Ahmad',
            confidence=0.95,
            source=ExtractionSource.PDF_TEXT_LAYER,
            citation=Citation(document_id='doc-1', page=1),
        )
    ]


async def _fake_finance_assessor(figures):
    return 'Adequate repayment capacity.', 0.9


async def _fake_credibility(source_url, snippet):
    return 0.9


def _fake_risk_assessor(
    financial_risk=0.2, compliance_risk=0.1, market_risk=0.2, confidence=0.9
):
    async def assessor(compliance, finance, market):
        return ComponentRiskScores(
            financial_risk, compliance_risk, market_risk, confidence
        )

    return assessor


def _fake_recommender(decision=RecommendationDecision.APPROVE, confidence=0.9):
    async def recommender(compliance, finance, risk, market):
        return DraftRecommendation(decision, 'Solid case.', [], confidence)

    return recommender


def _initial_state(
    compliance_requirements: list[str] | None = None,
) -> LoanAssessmentState:
    return {
        'document_id': 'doc-1',
        'pdf_bytes': _blank_pdf_bytes(),
        'compliance_requirements': compliance_requirements or [],
        'calculation_requests': [],
        'product_query': None,
        'sector': 'F&B',
        'region': 'Klang Valley',
        'precedent_query': None,
        'extraction_record': None,
        'extraction_decision': None,
        'compliance_checklist': None,
        'compliance_decision': None,
        'financial_analysis': None,
        'financial_decision': None,
        'market_brief': None,
        'risk_rating': None,
        'risk_decision': None,
        'recommendation': None,
        'recommendation_decision': None,
        'published_docx': None,
        'published_pptx': None,
        'publish_decision': None,
        'publish_error': None,
        'stage_log': [],
    }


def _compiled_graph(
    *,
    compliance_agent: ComplianceAgent | None = None,
    risk_assessor=None,
    recommender=None,
):
    document_agent = DocumentAgent(
        field_extractor=_fake_field_extractor,
        classifier=lambda _b: ('bank_statement', 0.9),
    )
    graph = build_loan_assessment_graph(
        document_agent=document_agent,
        compliance_agent=compliance_agent or ComplianceAgent(),
        finance_agent=FinanceAgent(assessor=_fake_finance_assessor),
        market_agent=MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=lambda _q: [],
            allowed_domains=frozenset({'example.com'}),
        ),
        risk_agent=RiskAgent(assessor=risk_assessor or _fake_risk_assessor()),
        recommendation_agent=RecommendationAgent(
            recommender=recommender or _fake_recommender()
        ),
    )
    return graph.compile(checkpointer=InMemorySaver())


async def _approve_through_happy_path(compiled, config, requirements=None):
    await compiled.ainvoke(_initial_state(requirements), config=config)
    await compiled.ainvoke(
        Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
    )  # confirm_extraction
    await compiled.ainvoke(
        Command(resume={'status': 'approved', 'actor': 'finance-officer'}),
        config=config,
    )  # financial_sign_off
    await compiled.ainvoke(
        Command(resume={'status': 'approved', 'actor': 'risk-officer'}), config=config
    )  # risk_review
    await compiled.ainvoke(
        Command(resume={'status': 'approved', 'actor': 'case-owner'}), config=config
    )  # recommendation_approval
    return await compiled.ainvoke(
        Command(resume={'status': 'approved', 'actor': 'committee-secretary'}),
        config=config,
    )  # publish_approval


class TestHappyPath:
    @pytest.mark.asyncio
    async def test_full_workflow_reaches_completion_with_artifacts(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-1'}}

        result = await _approve_through_happy_path(compiled, config)

        assert result['stage_log'][-1] == 'completion'
        assert result['published_docx'] is not None
        assert result['published_pptx'] is not None
        assert result['recommendation'].decision == RecommendationDecision.APPROVE

    @pytest.mark.asyncio
    async def test_parallel_branches_all_ran(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-2'}}

        await compiled.ainvoke(_initial_state(), config=config)
        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )

        assert {'compliance_check', 'finance_analysis', 'market_research'} <= set(
            result['stage_log']
        )
        assert result['compliance_checklist'] is not None
        assert result['financial_analysis'] is not None
        assert result['market_brief'] is not None

    @pytest.mark.asyncio
    async def test_no_hard_violation_skips_compliance_acknowledgment_interrupt(
        self,
    ) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-3'}}

        await compiled.ainvoke(_initial_state(), config=config)
        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )

        # Only one interrupt pending (financial_sign_off) — acknowledgment
        # was a silent pass-through, not a second pause.
        assert len(result['__interrupt__']) == 1
        assert result['__interrupt__'][0].value['type'] == 'financial_sign_off'


class TestExtractionRejection:
    @pytest.mark.asyncio
    async def test_rejection_halts_before_any_analysis(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-4'}}

        await compiled.ainvoke(_initial_state(), config=config)
        result = await compiled.ainvoke(
            Command(resume={'status': 'rejected', 'actor': 'officer-1'}), config=config
        )

        assert result['stage_log'] == [
            'document_extraction',
            'validation',
            'confirm_extraction',
            'completion',
        ]
        assert result['compliance_checklist'] is None
        assert result['financial_analysis'] is None
        assert result['market_brief'] is None


class TestFinancialSignOffRejection:
    @pytest.mark.asyncio
    async def test_rejection_halts_before_recommendation(self) -> None:
        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-5'}}

        await compiled.ainvoke(_initial_state(), config=config)
        await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )
        result = await compiled.ainvoke(
            Command(resume={'status': 'rejected', 'actor': 'finance-officer'}),
            config=config,
        )

        assert result['stage_log'][-1] == 'completion'
        # risk_synthesis already ran (it precedes financial_sign_off in the
        # chain) — rejecting the sign-off halts what comes *after* it
        # (risk_review, recommendation), not the already-completed synthesis.
        assert result['risk_rating'] is not None
        assert result['recommendation'] is None


class TestHardComplianceViolation:
    def _violating_compliance_agent(self) -> ComplianceAgent:
        async def lookup(requirement: str, ledger=None):
            """Stands in for a real RAG lookup, including its ledger write.

            The recording is not incidental: the workflow now runs §6.1
            verification on the finished checklist, so a double that returns a
            citation it never recorded is — correctly — indistinguishable from
            a fabrication and gets rejected. Recording keeps this double
            faithful to what `make_rag_policy_lookup` actually does.
            """
            from shared.schemas.knowledge import PolicyCitation, TrustTier

            citation = PolicyCitation(
                document_id='pol-1',
                version='v1',
                locator='1',
                trust_tier=TrustTier.APPROVED,
            )
            if ledger is not None:
                ledger.record_returned('rag_query', (citation.to_citable_ref(),))
            return [citation]

        async def checker(requirement, citations, record):
            return ComplianceStatus.FAIL, 'Business registration expired.'

        return ComplianceAgent(policy_lookup=lookup, checker=checker)

    @pytest.mark.asyncio
    async def test_hard_violation_triggers_extra_acknowledgment_interrupt(self) -> None:
        compiled = _compiled_graph(
            compliance_agent=self._violating_compliance_agent(),
            risk_assessor=_fake_risk_assessor(financial_risk=0.5),
        )
        config = {'configurable': {'thread_id': 'wf-6'}}

        await compiled.ainvoke(
            _initial_state(['valid business registration']), config=config
        )
        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )

        interrupt_types = {i.value['type'] for i in result['__interrupt__']}
        assert 'compliance_acknowledgment' in interrupt_types

    @pytest.mark.asyncio
    async def test_halted_acknowledgment_completes_without_recommendation(self) -> None:
        compiled = _compiled_graph(
            compliance_agent=self._violating_compliance_agent(),
            risk_assessor=_fake_risk_assessor(financial_risk=0.5),
        )
        config = {'configurable': {'thread_id': 'wf-7'}}

        await compiled.ainvoke(
            _initial_state(['valid business registration']), config=config
        )
        await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )
        # Resolve both pending interrupts (acknowledgment + financial sign-off).
        await compiled.ainvoke(
            Command(resume={'status': 'halted', 'actor': 'compliance-officer'}),
            config=config,
        )
        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'finance-officer'}),
            config=config,
        )
        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'risk-officer'}),
            config=config,
        )

        assert result['stage_log'][-1] == 'completion'
        assert result['recommendation'] is None

    @pytest.mark.asyncio
    async def test_acknowledged_violation_still_withholds_recommendation(self) -> None:
        """Documents the tension described in the module's own docstring:
        acknowledgment lets the workflow keep computing Risk, but
        agents/recommendation_agent's §5.8 escalation rule is unconditional."""

        compiled = _compiled_graph(
            compliance_agent=self._violating_compliance_agent(),
            risk_assessor=_fake_risk_assessor(financial_risk=0.5),
        )
        config = {'configurable': {'thread_id': 'wf-8'}}

        await compiled.ainvoke(
            _initial_state(['valid business registration']), config=config
        )
        await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'officer-1'}), config=config
        )
        await compiled.ainvoke(
            Command(resume={'status': 'acknowledged', 'actor': 'compliance-officer'}),
            config=config,
        )
        await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'finance-officer'}),
            config=config,
        )
        result = await compiled.ainvoke(
            Command(resume={'status': 'approved', 'actor': 'risk-officer'}),
            config=config,
        )

        assert result['risk_rating'] is not None
        assert result['risk_rating'].status.value == 'complete'
        # recommendation node ran (workflow wasn't halted, unlike the
        # previous test) but withheld — see this test's own docstring.
        assert result['stage_log'][-1] == 'recommendation'
        assert '__interrupt__' in result  # paused at recommendation_approval
        assert result['recommendation'] is not None
        assert result['recommendation'].decision is None
        assert result['recommendation'].withheld_reason is not None


class TestCitationVerificationIsLive:
    """§6.1 verification has to be *wired in*, not merely available.

    Every agent module accepts a ledger, but for a while no workflow passed
    one — so the control existed and protected nothing. These tests fail if
    that regresses: remove the ledger from the compliance node and the first
    one goes green when it should not.
    """

    @staticmethod
    def _fabricating_compliance_agent() -> ComplianceAgent:
        """A lookup that retrieves clause 1 but reports clause 9.9.

        The retrieval is real, so the ledger is populated — this is the
        dangerous shape, not an empty-ledger false positive: a well-formed
        citation to a neighbouring clause that was never actually returned.
        """

        async def lookup(requirement: str, ledger=None):
            from shared.schemas.knowledge import PolicyCitation, TrustTier

            retrieved = PolicyCitation(
                document_id='pol-1',
                version='v1',
                locator='1',
                trust_tier=TrustTier.APPROVED,
            )
            if ledger is not None:
                ledger.record_returned('rag_query', (retrieved.to_citable_ref(),))
            return [
                PolicyCitation(
                    document_id='pol-1',
                    version='v1',
                    locator='9.9',
                    trust_tier=TrustTier.APPROVED,
                )
            ]

        async def checker(requirement, citations, record):
            return ComplianceStatus.PASS, 'Satisfied.'

        return ComplianceAgent(policy_lookup=lookup, checker=checker)

    @pytest.mark.asyncio
    async def test_a_fabricated_citation_stops_the_workflow(self) -> None:
        compiled = _compiled_graph(
            compliance_agent=self._fabricating_compliance_agent()
        )
        config = {'configurable': {'thread_id': 'wf-cite-1'}}

        await compiled.ainvoke(
            _initial_state(['valid business registration']), config=config
        )

        with pytest.raises(FabricatedCitationError, match='pol-1@v1#9.9'):
            await compiled.ainvoke(
                Command(resume={'status': 'approved', 'actor': 'officer-1'}),
                config=config,
            )

    @pytest.mark.asyncio
    async def test_an_honest_citation_passes_through(self) -> None:
        """The counterpart, so the test above is known to be catching the
        fabrication rather than the workflow simply always failing here."""

        compiled = _compiled_graph()
        config = {'configurable': {'thread_id': 'wf-cite-2'}}

        result = await _approve_through_happy_path(compiled, config)

        assert result['compliance_checklist'] is not None
        assert result['stage_log'][-1] == 'completion'
