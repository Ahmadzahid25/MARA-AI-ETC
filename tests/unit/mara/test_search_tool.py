"""Unit tests for tools/search/search_tool.py."""

from __future__ import annotations

import pytest

from shared.schemas import (
    ToolExternalServiceError,
    ToolInputError,
    ToolPermissionError,
)
from tools.search.search_tool import SearchResult, run_search

ALLOWED = frozenset({'example.com', 'trusted-news.my'})


def _fake_engine(results: list[SearchResult]):
    def engine(sanitized_query: str) -> list[SearchResult]:
        return results

    return engine


class TestPermissions:
    def test_non_market_agent_denied(self) -> None:
        with pytest.raises(ToolPermissionError):
            run_search(
                'F&B sector outlook',
                caller_agent='finance_agent',
                allowed_domains=ALLOWED,
                engine=_fake_engine([]),
            )

    def test_market_agent_allowed(self) -> None:
        results = run_search(
            'F&B sector outlook',
            caller_agent='market_agent',
            allowed_domains=ALLOWED,
            engine=_fake_engine([]),
        )
        assert results == []


class TestSanitizationEnforcedAtBoundary:
    def test_pure_pii_query_rejected_before_engine_called(self) -> None:
        calls = []

        def engine(sanitized_query: str) -> list[SearchResult]:
            calls.append(sanitized_query)
            return []

        with pytest.raises(ToolInputError):
            run_search(
                '990101-14-5566',
                caller_agent='market_agent',
                allowed_domains=ALLOWED,
                engine=engine,
            )
        assert calls == []

    def test_engine_receives_sanitized_query_not_raw(self) -> None:
        captured = {}

        def engine(sanitized_query: str) -> list[SearchResult]:
            captured['query'] = sanitized_query
            return []

        run_search(
            'contact 012-3456789 about F&B sector trends',
            caller_agent='market_agent',
            allowed_domains=ALLOWED,
            engine=engine,
        )
        assert '012-3456789' not in captured['query']


class TestDomainAllowList:
    def test_results_outside_allow_list_are_filtered_out(self) -> None:
        results = run_search(
            'F&B sector outlook',
            caller_agent='market_agent',
            allowed_domains=ALLOWED,
            engine=_fake_engine(
                [
                    SearchResult(url='https://example.com/a', title='A', snippet='...'),
                    SearchResult(url='https://untrusted.example.org/b', title='B', snippet='...'),
                ]
            ),
        )
        assert len(results) == 1
        assert results[0].url == 'https://example.com/a'

    def test_www_prefix_is_normalized(self) -> None:
        results = run_search(
            'F&B sector outlook',
            caller_agent='market_agent',
            allowed_domains=ALLOWED,
            engine=_fake_engine(
                [SearchResult(url='https://www.example.com/a', title='A', snippet='...')]
            ),
        )
        assert len(results) == 1

    def test_empty_allow_list_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            run_search(
                'F&B sector outlook',
                caller_agent='market_agent',
                allowed_domains=frozenset(),
                engine=_fake_engine([]),
            )


class TestDefaultEngine:
    def test_no_engine_raises_external_service_error(self) -> None:
        with pytest.raises(ToolExternalServiceError):
            run_search(
                'F&B sector outlook', caller_agent='market_agent', allowed_domains=ALLOWED
            )


class TestAuditLogging:
    def test_success_logs_sanitized_query_and_domains_hit(self) -> None:
        entries = []
        run_search(
            'contact 012-3456789 about F&B sector trends',
            caller_agent='market_agent',
            allowed_domains=ALLOWED,
            engine=_fake_engine(
                [SearchResult(url='https://example.com/a', title='A', snippet='...')]
            ),
            audit_sink=entries.append,
        )
        assert len(entries) == 1
        assert '012-3456789' not in entries[0].metadata['sanitized_query']
        assert entries[0].metadata['domains_hit'] == ['example.com']
