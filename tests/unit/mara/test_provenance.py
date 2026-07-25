"""Citation-verification tests — docs/architecture/06-tool-architecture.md §6.1,
Review Board Finding A2.

The property under test is narrow and worth stating plainly: an agent cannot
make a citation valid by asserting it, only by having caused a tool to return
it. Everything below is a way of checking that the ledger cannot be talked into
accepting something it never saw.
"""

from __future__ import annotations

import pytest

from shared.provenance import (
    CitableRef,
    FabricatedCitationError,
    ProvenanceLedger,
)

POLICY_V3 = CitableRef(document_id='policy-1', version='v3', locator='4.2')
POLICY_V4 = CitableRef(document_id='policy-1', version='v4', locator='4.2')
OTHER_CLAUSE = CitableRef(document_id='policy-1', version='v3', locator='9.9')


def test_a_recorded_citation_verifies() -> None:
    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3,))

    result = ledger.verify((POLICY_V3,))

    assert result.ok
    assert result.verified == (POLICY_V3,)
    assert result.rejected == ()


def test_an_unrecorded_citation_is_rejected() -> None:
    """The fabrication case: well-formed, plausible, never retrieved."""

    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3,))

    result = ledger.verify((OTHER_CLAUSE,))

    assert not result.ok
    assert result.rejected == (OTHER_CLAUSE,)


def test_citing_a_different_version_than_was_retrieved_is_rejected() -> None:
    """§9.4: an audit of a March decision must see March's policy text. A
    citation that drifts to a newer version of the same clause is wrong in a way
    that reads as correct, which is exactly why version is part of identity."""

    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3,))

    assert ledger.verify((POLICY_V4,)).rejected == (POLICY_V4,)


def test_verification_fails_closed_on_an_empty_ledger() -> None:
    """ "No tool ran" and "the agent may cite freely" must never be the same
    state — the likeliest way to reach an empty ledger is a caller that forgot
    to pass one, and that must not read as permission."""

    assert ProvenanceLedger().verify((POLICY_V3,)).rejected == (POLICY_V3,)


def test_no_citations_verifies_trivially() -> None:
    """An agent with nothing to cite is not in violation — §5.4's
    NO_POLICY_FOUND path emits no citations and must not be blocked."""

    assert ProvenanceLedger().verify(()).ok


def test_partial_rejection_reports_both_sides() -> None:
    """§6.1 requires a rejected citation be flagged, which means naming which
    one failed — not collapsing the output to a single pass/fail."""

    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3,))

    result = ledger.verify((POLICY_V3, OTHER_CLAUSE))

    assert result.verified == (POLICY_V3,)
    assert result.rejected == (OTHER_CLAUSE,)


def test_require_verified_raises_and_names_the_fabrication() -> None:
    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3,))

    with pytest.raises(FabricatedCitationError) as excinfo:
        ledger.require_verified((OTHER_CLAUSE,))

    assert excinfo.value.rejected == (OTHER_CLAUSE,)
    assert 'policy-1@v3#9.9' in str(excinfo.value)


def test_require_verified_passes_when_everything_was_retrieved() -> None:
    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3, OTHER_CLAUSE))

    ledger.require_verified((OTHER_CLAUSE, POLICY_V3))


def test_returned_by_attributes_refs_to_the_tool_that_returned_them() -> None:
    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3,))
    ledger.record_returned('structured_database_query', (OTHER_CLAUSE,))

    assert ledger.returned_by('rag_query') == frozenset({POLICY_V3})
    assert ledger.returned_by('structured_database_query') == frozenset({OTHER_CLAUSE})
    assert ledger.returned_by('web_search') == frozenset()
    assert ledger.all_returned == frozenset({POLICY_V3, OTHER_CLAUSE})


def test_recording_is_idempotent() -> None:
    ledger = ProvenanceLedger()
    ledger.record_returned('rag_query', (POLICY_V3,))
    ledger.record_returned('rag_query', (POLICY_V3,))

    assert len(ledger) == 1
