"""Compliance Agent against a real RAG-backed policy lookup — Milestone 2.

Covers the seam Milestone 1 deliberately stubbed
(agents/compliance_agent/compliance_agent.py's module docstring: "Replacing the
stub policy_lookup/checker with real Knowledge Service-backed implementations is
the Milestone 2 task; the call sites here don't need to change when that
happens") and the end-to-end citation-verification path §6.1 requires.
"""

from __future__ import annotations

from datetime import date

import pytest

from agents.compliance_agent import ComplianceAgent, make_rag_policy_lookup
from shared.provenance import FabricatedCitationError, ProvenanceLedger
from shared.schemas.compliance import ComplianceStatus
from shared.schemas.documents import (
    DocumentClassification,
    DocumentExtractionRecord,
)
from shared.schemas.knowledge import (
    DocumentKind,
    PolicyCitation,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
    SensitivityClass,
)

CLAUSE = RetrievedChunk(
    document_id='policy-1',
    version='v3',
    locator='4.2',
    text='Applicants must hold a valid business registration.',
    relevance=0.93,
    document_kind=DocumentKind.POLICY,
    sensitivity=SensitivityClass.INTERNAL,
)


class StubBackend:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.queries: list[RetrievalQuery] = []

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        self.queries.append(query)
        return self.result


def _record() -> DocumentExtractionRecord:
    return DocumentExtractionRecord(
        document_id='doc-1',
        classification=DocumentClassification(
            document_type='business_registration', confidence=0.95
        ),
        fields=[],
    )


async def _passing_checker(requirement, citations, record):
    return ComplianceStatus.PASS, 'Satisfied.'


@pytest.mark.asyncio
async def test_lookup_scopes_retrieval_to_currently_effective_policy() -> None:
    """§9.3: similarity alone will surface a superseded clause that reads almost
    identically to the current one, so the filter is not optional."""

    backend = StubBackend(RetrievalResult(chunks=(CLAUSE,)))
    lookup = make_rag_policy_lookup(backend, ledger=ProvenanceLedger())

    await lookup('valid business registration')

    (query,) = backend.queries
    assert query.filters.document_kinds == frozenset({DocumentKind.POLICY})
    assert query.filters.include_superseded is False


@pytest.mark.asyncio
async def test_checklist_cites_the_retrieved_clause_with_its_version() -> None:
    backend = StubBackend(RetrievalResult(chunks=(CLAUSE,)))
    ledger = ProvenanceLedger()
    agent = ComplianceAgent(
        policy_lookup=make_rag_policy_lookup(backend, ledger=ledger),
        checker=_passing_checker,
    )

    checklist = await agent.check_compliance(
        'doc-1', _record(), ['valid business registration'], ledger=ledger
    )

    citation = checklist.items[0].policy_citation
    assert citation == PolicyCitation(
        document_id='policy-1', version='v3', locator='4.2', relevance=0.93
    )


@pytest.mark.asyncio
async def test_no_confident_match_reports_no_policy_found() -> None:
    """§9.5 + §5.4: a weak retrieval is reported honestly, never treated as
    support for a pass."""

    backend = StubBackend(
        RetrievalResult(no_confident_match=True, withheld_below_threshold=3)
    )
    ledger = ProvenanceLedger()
    agent = ComplianceAgent(
        policy_lookup=make_rag_policy_lookup(backend, ledger=ledger),
        checker=_passing_checker,
    )

    checklist = await agent.check_compliance(
        'doc-1', _record(), ['some obscure requirement'], ledger=ledger
    )

    item = checklist.items[0]
    assert item.status is ComplianceStatus.NO_POLICY_FOUND
    assert item.policy_citation is None


@pytest.mark.asyncio
async def test_a_fabricated_citation_is_rejected_before_the_checklist_returns() -> None:
    """Finding A2, end to end: a checker that invents a clause the corpus never
    returned must not produce an officer-facing finding."""

    backend = StubBackend(RetrievalResult(chunks=(CLAUSE,)))
    ledger = ProvenanceLedger()

    async def _fabricating_lookup(requirement: str):
        # Retrieval genuinely happens — so the ledger is populated — but the
        # citation attached to the finding names a different clause.
        await make_rag_policy_lookup(backend, ledger=ledger)(requirement)
        return [PolicyCitation(document_id='policy-1', version='v3', locator='9.9')]

    agent = ComplianceAgent(policy_lookup=_fabricating_lookup, checker=_passing_checker)

    with pytest.raises(FabricatedCitationError, match='policy-1@v3#9.9'):
        await agent.check_compliance(
            'doc-1', _record(), ['valid business registration'], ledger=ledger
        )


@pytest.mark.asyncio
async def test_verification_is_skipped_when_no_ledger_is_supplied() -> None:
    """The default stub lookup retrieves nothing and cites nothing; forcing a
    ledger on that path would fail closed for no benefit."""

    agent = ComplianceAgent()

    checklist = await agent.check_compliance('doc-1', _record(), ['anything'])

    assert checklist.items[0].status is ComplianceStatus.NO_POLICY_FOUND


def test_a_superseded_citation_is_flagged_as_stale() -> None:
    """Milestone 2 acceptance criterion (docs/architecture/14-roadmap.md §14.4):
    "a superseded-policy staleness check correctly flags an outdated citation"."""

    cited = PolicyCitation(
        document_id='policy-1',
        version='v3',
        locator='4.2',
        superseded_on=date(2026, 1, 31),
    )

    assert cited.is_stale_as_of(date(2026, 3, 1)) is True
    # Still correct for a decision made while v3 was in force — historical, not
    # wrong, which is why staleness is relative to when you ask.
    assert cited.is_stale_as_of(date(2026, 1, 1)) is False


def test_a_current_citation_is_not_stale() -> None:
    current = PolicyCitation(document_id='policy-1', version='v4', locator='4.2')

    assert current.is_stale_as_of(date(2026, 3, 1)) is False
