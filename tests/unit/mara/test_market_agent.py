"""Unit tests for agents/market_agent/market_agent.py."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from agents.market_agent.market_agent import (
    INSUFFICIENT_DATA_NOTE,
    LIVE_SEARCH_UNAVAILABLE_NOTE,
    MarketAgent,
)
from shared.schemas import ToolExternalServiceError
from shared.schemas.knowledge import (
    DocumentKind,
    RetrievalResult,
    RetrievedChunk,
    SensitivityClass,
    TrustTier,
)
from tools.search.search_tool import SearchResult

ALLOWED = frozenset({'trusted-news.my'})


async def _fake_credibility(source_url: str, snippet: str) -> float:
    return 0.9


class _StubBackend:
    def __init__(self, result: RetrievalResult | None = None) -> None:
        self.result = result or RetrievalResult()
        self.queries = []

    async def retrieve(self, query):
        self.queries.append(query)
        return self.result


def _search_engine(results: list[SearchResult]):
    def engine(sanitized_query: str) -> list[SearchResult]:
        return results

    return engine


def _failing_search_engine():
    def engine(sanitized_query: str) -> list[SearchResult]:
        raise ToolExternalServiceError('provider down')

    return engine


class TestGatherMarketContext:
    @pytest.mark.asyncio
    async def test_claims_cite_source_and_retrieval_date(self) -> None:
        agent = MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=_search_engine(
                [
                    SearchResult(
                        url='https://trusted-news.my/fnb-outlook',
                        title='F&B outlook',
                        snippet='F&B sector is projected to grow 5% in Klang Valley.',
                        retrieved_at=datetime(2026, 1, 1, tzinfo=UTC),
                    )
                ]
            ),
            backend=_StubBackend(),
            allowed_domains=ALLOWED,
        )

        brief = await agent.gather_market_context('F&B', 'Klang Valley')

        assert len(brief.claims) == 1
        assert brief.claims[0].source_url == 'https://trusted-news.my/fnb-outlook'
        assert brief.claims[0].retrieved_at == datetime(2026, 1, 1, tzinfo=UTC)
        assert brief.claims[0].credibility_score == 0.9
        assert brief.live_search_available is True
        assert brief.note == ''

    @pytest.mark.asyncio
    async def test_search_failure_degrades_to_knowledge_base_only(self) -> None:
        cached_chunk = RetrievedChunk(
            document_id='market-fnb-klang-valley',
            version='v1',
            locator='1',
            text='Cached: F&B sector stable.',
            relevance=0.7,
            document_kind=DocumentKind.MARKET_DATA,
            sensitivity=SensitivityClass.INTERNAL,
            trust_tier=TrustTier.APPROVED,
            # §9.7: market data carries a freshness window, so a cache entry
            # that is meant to be usable has to be dated. Without cached_at the
            # RAG tool cannot establish this finding's age and withholds it —
            # covered by test_market_data_freshness below.
            cached_at=date.today(),
        )
        agent = MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=_failing_search_engine(),
            backend=_StubBackend(RetrievalResult(chunks=(cached_chunk,))),
            allowed_domains=ALLOWED,
        )

        brief = await agent.gather_market_context('F&B', 'Klang Valley')

        assert brief.live_search_available is False
        assert LIVE_SEARCH_UNAVAILABLE_NOTE in brief.note
        assert len(brief.claims) == 1
        assert brief.claims[0].claim == 'Cached: F&B sector stable.'

    @pytest.mark.asyncio
    async def test_no_claims_reports_insufficient_data(self) -> None:
        agent = MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=_search_engine([]),
            backend=_StubBackend(),
            allowed_domains=ALLOWED,
        )

        brief = await agent.gather_market_context('Widgets', 'Sabah')

        assert brief.claims == []
        assert INSUFFICIENT_DATA_NOTE in brief.note

    @pytest.mark.asyncio
    async def test_low_credibility_claims_are_labeled_not_dropped(self) -> None:
        async def low_credibility(source_url: str, snippet: str) -> float:
            return 0.3

        agent = MarketAgent(
            credibility_assessor=low_credibility,
            search_engine=_search_engine(
                [
                    SearchResult(
                        url='https://trusted-news.my/x',
                        title='x',
                        snippet='a shaky claim',
                    )
                ]
            ),
            backend=_StubBackend(),
            allowed_domains=ALLOWED,
        )

        brief = await agent.gather_market_context('F&B', 'Klang Valley')

        assert len(brief.claims) == 1
        assert brief.claims[0].is_low_credibility(threshold=0.7) is True

    @pytest.mark.asyncio
    async def test_cache_writer_invoked_when_claims_present(self) -> None:
        written = []

        async def cache_writer(brief):
            written.append(brief)

        agent = MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=_search_engine(
                [SearchResult(url='https://trusted-news.my/x', title='x', snippet='y')]
            ),
            backend=_StubBackend(),
            cache_writer=cache_writer,
            allowed_domains=ALLOWED,
        )

        await agent.gather_market_context('F&B', 'Klang Valley')

        assert len(written) == 1

    @pytest.mark.asyncio
    async def test_cache_writer_not_invoked_when_no_claims(self) -> None:
        written = []

        async def cache_writer(brief):
            written.append(brief)

        agent = MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=_search_engine([]),
            backend=_StubBackend(),
            cache_writer=cache_writer,
            allowed_domains=ALLOWED,
        )

        await agent.gather_market_context('F&B', 'Klang Valley')

        assert written == []

    @pytest.mark.asyncio
    async def test_rag_query_scopes_to_market_data_document_kind(self) -> None:
        backend = _StubBackend()
        agent = MarketAgent(
            credibility_assessor=_fake_credibility,
            search_engine=_search_engine([]),
            backend=backend,
            allowed_domains=ALLOWED,
        )

        await agent.gather_market_context('F&B', 'Klang Valley')

        (query,) = backend.queries
        assert query.filters.document_kinds == frozenset({DocumentKind.MARKET_DATA})
