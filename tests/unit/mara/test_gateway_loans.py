"""Gateway tests for the Loan Assessment endpoints — exercised against a real
compiled graph (InMemorySaver, fake tool-level engines), not a mocked
workflow, so these prove the actual HTTP -> agent -> workflow -> gate wiring.

The bulk of what's worth testing here is authorization. §10.2 gives each of
the six gates a different approver, and being signed in is not by itself
permission to act at the one in front of you.
"""

from __future__ import annotations

import io
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import InMemorySaver
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
from services.api_gateway.app import create_app
from services.api_gateway.auth import Principal, get_current_principal
from shared.schemas.documents import Citation, ExtractedField, ExtractionSource
from shared.schemas.recommendation import RecommendationDecision
from workflows.loan_assessment.loan_assessment import build_loan_assessment_graph

OFFICER = 'entrepreneurship_officer'
COMPLIANCE = 'compliance_officer'
FINANCE = 'finance_officer'
RISK = 'risk_officer'


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
            citation=Citation(document_id='doc', page=1),
        )
    ]


def _fake_classifier(file_bytes: bytes) -> tuple[str, float]:
    return 'business_registration', 0.95


async def _fake_assessor(figures):
    return 'Adequate repayment capacity.', 0.9


async def _fake_credibility(source_url, snippet):
    return 0.9


async def _fake_risk_assessor(compliance, finance, market):
    return ComponentRiskScores(0.2, 0.1, 0.2, 0.9)


async def _fake_recommender(compliance, finance, risk, market):
    return DraftRecommendation(RecommendationDecision.APPROVE, 'Sound.', [], 0.9)


@contextmanager
def _client(roles: frozenset[str]) -> Iterator[TestClient]:
    """Context-managed so the app's lifespan runs — without it the injected
    graph is never placed on ``app.state`` and every route 500s."""

    graph = build_loan_assessment_graph(
        DocumentAgent(
            field_extractor=_fake_field_extractor, classifier=_fake_classifier
        ),
        ComplianceAgent(),
        FinanceAgent(assessor=_fake_assessor),
        MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=lambda _q: [],
            allowed_domains=frozenset({'example.com'}),
        ),
        RiskAgent(assessor=_fake_risk_assessor),
        RecommendationAgent(recommender=_fake_recommender),
    )
    app = create_app(loan_workflow=graph.compile(checkpointer=InMemorySaver()))
    app.dependency_overrides[get_current_principal] = lambda: Principal(
        subject='officer-1', realm_roles=roles
    )
    with TestClient(app) as client:
        yield client


def _start(client: TestClient) -> dict:
    response = client.post(
        '/loans/assessments',
        files={'file': ('a.pdf', _blank_pdf_bytes(), 'application/pdf')},
        data={'sector': 'F&B', 'region': 'Klang Valley'},
    )
    assert response.status_code == 200, response.text
    return response.json()


class TestStartingAnAssessment:
    def test_runs_to_the_first_gate_and_names_it(self) -> None:
        with _client(frozenset({OFFICER})) as client:
            body = _start(client)

        assert body['status'] == 'pending_approval'
        assert body['pending_gate'] == 'confirm_extraction'
        assert body['thread_id']

    def test_the_pending_payload_is_passed_through_for_the_officer(self) -> None:
        """§10.4: an approval request must show the output under review, not a
        bare 'something needs approving'."""

        with _client(frozenset({OFFICER})) as client:
            body = _start(client)

        assert body['pending_payload']['extraction_record'] is not None


class TestGateAuthorization:
    """§10.2 — the part that authentication alone does not give you."""

    def test_the_wrong_role_is_refused_at_the_first_gate(self) -> None:
        with _client(frozenset({FINANCE})) as client:
            thread_id = _start(client)['thread_id']

            response = client.post(
                f'/loans/assessments/{thread_id}/decision',
                json={'action': 'approve'},
            )

            assert response.status_code == 403
            assert 'confirm_extraction' in response.json()['detail']

    def test_the_right_role_is_accepted(self) -> None:
        with _client(frozenset({OFFICER})) as client:
            thread_id = _start(client)['thread_id']

            response = client.post(
                f'/loans/assessments/{thread_id}/decision',
                json={'action': 'approve'},
            )

            assert response.status_code == 200, response.text
            assert response.json()['acted_gate'] == 'confirm_extraction'

    def test_authorization_follows_the_gate_as_the_workflow_advances(self) -> None:
        """The point of reading the gate from workflow state rather than the
        request: the same officer, same endpoint, is allowed at one gate and
        refused at the next."""

        with _client(frozenset({OFFICER, COMPLIANCE})) as client:
            thread_id = _start(client)['thread_id']

            first = client.post(
                f'/loans/assessments/{thread_id}/decision', json={'action': 'approve'}
            )
            assert first.status_code == 200, first.text
            # No hard violation, so the next gate is the Finance Officer's.
            assert first.json()['pending_gate'] == 'financial_sign_off'

            second = client.post(
                f'/loans/assessments/{thread_id}/decision', json={'action': 'approve'}
            )
            assert second.status_code == 403
            assert 'financial_sign_off' in second.json()['detail']

    def test_holding_the_next_gates_role_lets_the_workflow_advance(self) -> None:
        with _client(frozenset({OFFICER, FINANCE, RISK})) as client:
            thread_id = _start(client)['thread_id']

            client.post(
                f'/loans/assessments/{thread_id}/decision', json={'action': 'approve'}
            )
            finance = client.post(
                f'/loans/assessments/{thread_id}/decision', json={'action': 'approve'}
            )

            assert finance.status_code == 200, finance.text
            assert finance.json()['acted_gate'] == 'financial_sign_off'
            assert finance.json()['pending_gate'] == 'risk_review'


class TestSequencingErrors:
    def test_a_decision_on_an_unknown_workflow_is_a_conflict_not_a_crash(
        self,
    ) -> None:
        with _client(frozenset({OFFICER})) as client:
            response = client.post(
                '/loans/assessments/never-started/decision', json={'action': 'approve'}
            )

            assert response.status_code == 409

    @pytest.mark.parametrize('action', ['approve', 'reject'])
    def test_a_rejection_is_recorded_like_an_approval(self, action: str) -> None:
        """Both are attributed decisions §10.7 says are retained — a rejection
        is not an error path."""

        with _client(frozenset({OFFICER})) as client:
            thread_id = _start(client)['thread_id']

            response = client.post(
                f'/loans/assessments/{thread_id}/decision', json={'action': action}
            )

            assert response.status_code == 200, response.text
