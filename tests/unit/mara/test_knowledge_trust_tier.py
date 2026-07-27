"""§9.7 trust tiers and market-data freshness.

ACCB Mandatory Change 2 / Review Board Finding C3
(docs/architecture/review/03-data-and-security-review.md Red Team #7). The
attack these tests exist to close:

    The Market Agent gathers findings from the open internet and writes them
    into Knowledge Memory. If that content is retrievable as ordinary corpus
    knowledge, a single run against a low-quality or adversarially-optimized
    source becomes silently-trusted context for every future Risk and
    Recommendation Agent run in that sector — with no human ever having
    reviewed it.

docs/architecture/14-roadmap.md §14.5 lists this as a launch precondition for
the Market Agent existing at all, not as follow-on hardening. So these are
containment tests, not coverage: each one is written so that removing the
corresponding enforcement makes it fail.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from services.knowledge_service.dify_adapter import DifyAdapter
from shared.agent_profiles import AGENT_PROFILES, profile_for
from shared.provenance import FabricatedCitationError, ProvenanceLedger
from shared.schemas import ToolPermissionError
from shared.schemas.knowledge import (
    MARKET_DATA_FRESHNESS_DAYS,
    DocumentKind,
    PolicyCitation,
    RetrievalFilters,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
    SensitivityClass,
    TrustTier,
)
from tools.rag.rag_tool import TOOL_NAME, rag_query

TODAY = date(2026, 7, 27)

# The two agents whose output drives a lending decision. §9.7 names them
# explicitly as the ones that must treat provisional content as unverified.
DECISION_AGENTS = ('risk_agent', 'recommendation_agent')


def _chunk(
    *,
    tier: TrustTier = TrustTier.APPROVED,
    kind: DocumentKind = DocumentKind.POLICY,
    cached_at: date | None = None,
    locator: str = '4.2',
) -> RetrievedChunk:
    return RetrievedChunk(
        document_id='doc-1',
        version='v1',
        locator=locator,
        text='Sector outlook is stable.',
        relevance=0.9,
        document_kind=kind,
        sensitivity=SensitivityClass.INTERNAL,
        trust_tier=tier,
        cached_at=cached_at,
    )


class StubBackend:
    """Returns exactly what it is told to, ignoring the query's filters.

    Modelling Dify honestly: its metadata filtering is configuration we send,
    not code we own, so the tool cannot assume the filter was applied. A stub
    that dutifully filtered itself would test nothing.
    """

    def __init__(self, *chunks: RetrievedChunk) -> None:
        self.result = RetrievalResult(chunks=chunks)
        self.calls: list[RetrievalQuery] = []

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        self.calls.append(query)
        return self.result


def _query(**filter_kwargs: object) -> RetrievalQuery:
    return RetrievalQuery(
        query='sector outlook',
        filters=RetrievalFilters(effective_on=TODAY, **filter_kwargs),  # type: ignore[arg-type]
    )


# ── The profile grant itself (§9.7 via shared/agent_profiles) ──


def test_only_the_market_agent_may_read_the_low_trust_tier() -> None:
    """The grant is narrow by construction, not by convention.

    Asserted over the whole registry rather than on the Market Agent alone, so
    that adding a profile with the flag set — or flipping it on an existing one
    — fails here and has to be argued for, which is the governance point of
    keeping autonomy in one registry.
    """

    granted = {
        name
        for name, profile in AGENT_PROFILES.items()
        if profile.may_read_provisional_knowledge
    }
    assert granted == {'market_agent'}


def test_the_decision_agents_specifically_are_not_granted_it() -> None:
    for name in DECISION_AGENTS:
        assert profile_for(name).may_read_provisional_knowledge is False


# ── Request side: a caller cannot ask for what it may not read ──


@pytest.mark.parametrize('caller', DECISION_AGENTS)
@pytest.mark.asyncio
async def test_an_ungranted_caller_asking_for_provisional_is_rejected(
    caller: str,
) -> None:
    backend = StubBackend(_chunk())

    with pytest.raises(ToolPermissionError, match='low-trust tier'):
        await rag_query(
            _query(include_provisional=True), caller_agent=caller, backend=backend
        )

    # Rejected before the backend was reached — the request never went out.
    assert backend.calls == []


@pytest.mark.asyncio
async def test_the_request_is_refused_rather_than_quietly_narrowed() -> None:
    """Failing loudly matters more than failing safe here.

    Silently rewriting include_provisional to False would also keep the content
    out, but it would leave the caller believing it had searched the provisional
    tier and found nothing — a false negative on the exact question the tier
    exists to make answerable.
    """

    with pytest.raises(ToolPermissionError):
        await rag_query(
            _query(include_provisional=True),
            caller_agent='risk_agent',
            backend=StubBackend(_chunk()),
        )


@pytest.mark.asyncio
async def test_the_market_agent_may_ask_for_it() -> None:
    provisional = _chunk(
        tier=TrustTier.PROVISIONAL, kind=DocumentKind.MARKET_DATA, cached_at=TODAY
    )
    result = await rag_query(
        _query(include_provisional=True),
        caller_agent='market_agent',
        backend=StubBackend(provisional),
    )

    assert len(result.chunks) == 1
    # Readable, but still labeled — permission to read is not a promotion.
    assert result.chunks[0].trust_tier is TrustTier.PROVISIONAL


# ── Receive side: the backend is not trusted to have filtered ──


@pytest.mark.parametrize('caller', DECISION_AGENTS)
@pytest.mark.asyncio
async def test_provisional_chunks_are_withheld_even_when_the_backend_returns_them(
    caller: str,
) -> None:
    """The check that actually carries the control.

    The request-side check only stops a caller that asks. This one stops a
    backend that answers with content nobody asked for — which is the realistic
    failure, since the tier filter is a Dify metadata condition that depends on
    ingestion having written mara_trust_tier correctly.
    """

    backend = StubBackend(
        _chunk(locator='1.1'),
        _chunk(tier=TrustTier.PROVISIONAL, locator='2.2'),
    )

    result = await rag_query(_query(), caller_agent=caller, backend=backend)

    assert [c.locator for c in result.chunks] == ['1.1']
    assert result.withheld_unverified == 1


@pytest.mark.asyncio
async def test_withholding_is_counted_not_silent() -> None:
    """ "Nothing in the corpus" and "nothing approved yet" need different
    responses — one reports a gap, the other chases an approval."""

    result = await rag_query(
        _query(),
        caller_agent='risk_agent',
        backend=StubBackend(_chunk(tier=TrustTier.PROVISIONAL)),
    )

    assert result.chunks == ()
    assert result.withheld_unverified == 1


@pytest.mark.asyncio
async def test_a_withheld_chunk_is_not_recorded_in_the_ledger() -> None:
    """The provenance ledger must not become a way around the trust boundary.

    §6.1 verification passes a citation when the ledger says the tool returned
    it. If the tool recorded chunks it then withheld, an agent could cite
    unapproved content and have that citation verify — the two controls would
    cancel out. Recording therefore happens after §9.7 filtering, and this test
    fails if that order is reversed.
    """

    ledger = ProvenanceLedger()
    provisional = _chunk(tier=TrustTier.PROVISIONAL)

    await rag_query(
        _query(),
        caller_agent='risk_agent',
        backend=StubBackend(provisional),
        ledger=ledger,
    )

    assert not ledger.returned_by(TOOL_NAME)
    with pytest.raises(FabricatedCitationError):
        ledger.require_verified((provisional.to_citable_ref(),))


# ── Market-data freshness (§9.7) ──


@pytest.mark.asyncio
async def test_market_data_past_the_freshness_window_is_withheld() -> None:
    stale = _chunk(
        kind=DocumentKind.MARKET_DATA,
        cached_at=TODAY - timedelta(days=MARKET_DATA_FRESHNESS_DAYS + 1),
    )

    result = await rag_query(
        _query(), caller_agent='market_agent', backend=StubBackend(stale)
    )

    assert result.chunks == ()
    assert result.withheld_expired == 1
    # §9.7: "a fresh search is triggered instead of serving stale market
    # context silently" — this is the signal that triggers it.
    assert result.needs_fresh_search() is True


@pytest.mark.asyncio
async def test_market_data_inside_the_window_is_served() -> None:
    fresh = _chunk(
        kind=DocumentKind.MARKET_DATA,
        cached_at=TODAY - timedelta(days=MARKET_DATA_FRESHNESS_DAYS - 1),
    )

    result = await rag_query(
        _query(), caller_agent='market_agent', backend=StubBackend(fresh)
    )

    assert len(result.chunks) == 1
    assert result.needs_fresh_search() is False


@pytest.mark.asyncio
async def test_the_per_sector_override_is_honoured() -> None:
    """§9.7's window is "default 90 days, configurable per sector"."""

    chunk = _chunk(kind=DocumentKind.MARKET_DATA, cached_at=TODAY - timedelta(days=30))

    tight = await rag_query(
        _query(max_market_data_age_days=7),
        caller_agent='market_agent',
        backend=StubBackend(chunk),
    )
    assert tight.chunks == ()
    assert tight.withheld_expired == 1

    loose = await rag_query(
        _query(max_market_data_age_days=60),
        caller_agent='market_agent',
        backend=StubBackend(chunk),
    )
    assert len(loose.chunks) == 1


@pytest.mark.asyncio
async def test_undated_market_data_is_treated_as_expired() -> None:
    """Fail closed: an age that cannot be established is not evidence of
    freshness. The cost is a redundant search; the alternative is a lending
    decision resting on market data of unknown vintage."""

    result = await rag_query(
        _query(),
        caller_agent='market_agent',
        backend=StubBackend(_chunk(kind=DocumentKind.MARKET_DATA, cached_at=None)),
    )

    assert result.chunks == ()
    assert result.withheld_expired == 1


@pytest.mark.asyncio
async def test_policy_content_never_expires_on_age() -> None:
    """Expiry is a property of the market-data cache alone.

    Ageing out policy would be backwards — a clause unchanged for years is
    settled, not stale. Policy currency is decided by effective_from /
    superseded_on, which is a different question.
    """

    ancient = _chunk(
        kind=DocumentKind.POLICY, cached_at=TODAY - timedelta(days=365 * 10)
    )

    result = await rag_query(
        _query(), caller_agent='compliance_agent', backend=StubBackend(ancient)
    )

    assert len(result.chunks) == 1
    assert result.withheld_expired == 0


def test_is_expired_as_of_ignores_non_market_kinds() -> None:
    for kind in DocumentKind:
        chunk = _chunk(kind=kind, cached_at=TODAY - timedelta(days=1000))
        expired = chunk.is_expired_as_of(TODAY)
        assert expired is (kind is DocumentKind.MARKET_DATA)


# ── The tier has to survive into what the officer reads ──


def test_the_tier_travels_from_chunk_into_the_citation() -> None:
    """A provisional citation rendered indistinguishably from an approved one
    would defeat the control at the last step — §10.4 requires the officer see
    the evidence behind a claim, and "nobody has reviewed this source" is part
    of that evidence."""

    citation = PolicyCitation.from_chunk(_chunk(tier=TrustTier.PROVISIONAL))

    assert citation.trust_tier is TrustTier.PROVISIONAL
    assert citation.is_provisional() is True

    approved = PolicyCitation.from_chunk(_chunk(tier=TrustTier.APPROVED))
    assert approved.is_provisional() is False


def test_a_citation_cannot_be_built_without_stating_its_tier() -> None:
    with pytest.raises(ValueError, match='trust_tier'):
        PolicyCitation(document_id='d', version='v', locator='1')  # type: ignore[call-arg]


# ── The Dify boundary maps unknown provenance to the untrusted tier ──


def _dify_record(**metadata: str) -> dict:
    return {
        'score': 0.9,
        'segment': {
            'content': 'Sector outlook is stable.',
            'document': {
                'metadata': {
                    'mara_document_id': 'doc-1',
                    'mara_version': 'v1',
                    'mara_locator': '4.2',
                    'mara_document_kind': 'policy',
                    **metadata,
                }
            },
        },
    }


@pytest.mark.parametrize(
    'metadata',
    [
        pytest.param({}, id='absent'),
        pytest.param({'mara_trust_tier': ''}, id='empty'),
        pytest.param({'mara_trust_tier': 'Approved'}, id='wrong-case'),
        pytest.param({'mara_trust_tier': 'aproved'}, id='misspelled'),
        pytest.param({'mara_trust_tier': 'ratified'}, id='future-schema-value'),
    ],
)
def test_an_unreadable_trust_tier_maps_to_provisional(metadata: dict) -> None:
    """The one mapping in the adapter that must not be lenient.

    Every other unparseable field there degrades to a usable default, because a
    missing effective_from or a malformed date should not cost a whole
    retrieval. The tier is different in kind: content whose approval status
    cannot be established has, as far as this system can demonstrate, not been
    approved. An ingestion bug that drops the metadata must not quietly promote
    unreviewed material into Risk and Recommendation.
    """

    chunk = DifyAdapter._record_to_chunk(_dify_record(**metadata), 0.9)

    assert chunk is not None
    assert chunk.trust_tier is TrustTier.PROVISIONAL


def test_an_explicit_approved_tier_is_honoured() -> None:
    chunk = DifyAdapter._record_to_chunk(_dify_record(mara_trust_tier='approved'), 0.9)

    assert chunk is not None
    assert chunk.trust_tier is TrustTier.APPROVED


def test_the_adapter_asks_dify_to_exclude_provisional_by_default() -> None:
    """Belt and braces, and deliberately so.

    Narrowing server-side keeps unapproved text out of the response entirely
    rather than fetching it and discarding it. It is not the control — the tool
    re-checks every chunk — because this condition depends on Dify honouring a
    filter and on ingestion having written the field, neither of which this
    system can verify from here.
    """

    adapter = DifyAdapter.__new__(DifyAdapter)
    adapter._dataset_id = 'ds-1'

    payload = adapter._build_payload(RetrievalQuery(query='x'))
    conditions = payload['retrieval_model']['metadata_condition']['conditions']

    assert {
        'key': 'mara_trust_tier',
        'comparator': '=',
        'value': 'approved',
    } in conditions

    opted_in = adapter._build_payload(
        RetrievalQuery(query='x', filters=RetrievalFilters(include_provisional=True))
    )
    keys = [
        c['key']
        for c in opted_in['retrieval_model']
        .get('metadata_condition', {})
        .get('conditions', [])
    ]
    assert 'mara_trust_tier' not in keys


def test_a_chunk_cannot_be_built_without_stating_its_tier() -> None:
    """No default, deliberately. APPROVED would let a backend that forgot the
    mapping launder unreviewed content into the decision path; PROVISIONAL
    would silently downgrade the whole approved corpus."""

    with pytest.raises(ValueError, match='trust_tier'):
        RetrievedChunk(  # type: ignore[call-arg]
            document_id='d',
            version='v',
            locator='1',
            text='t',
            relevance=0.5,
            document_kind=DocumentKind.POLICY,
            sensitivity=SensitivityClass.INTERNAL,
        )
