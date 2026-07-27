"""Unit tests for tools/search/query_sanitizer.py."""

from __future__ import annotations

import pytest

from shared.schemas import ToolInputError
from tools.search.query_sanitizer import sanitize_query


class TestStructuredPIIRemoval:
    def test_ic_number_is_stripped(self) -> None:
        result = sanitize_query(
            'F&B outlet run by owner with IC 990101-14-5566 in Klang Valley'
        )
        assert '990101-14-5566' not in result
        assert 'F&B outlet' in result

    def test_bare_12_digit_ic_is_stripped(self) -> None:
        result = sanitize_query('applicant 990101145566 runs a bakery in Ipoh')
        assert '990101145566' not in result

    def test_business_registration_number_is_stripped(self) -> None:
        result = sanitize_query('registration 123456-X bakery outlook Ipoh')
        assert '123456-X' not in result
        assert 'bakery outlook' in result

    def test_phone_number_is_stripped(self) -> None:
        result = sanitize_query('contact 012-3456789 about F&B sector trends')
        assert '012-3456789' not in result
        assert 'F&B sector trends' in result

    def test_email_is_stripped(self) -> None:
        result = sanitize_query('owner@example.com bakery sector Penang')
        assert 'owner@example.com' not in result

    def test_street_address_is_stripped(self) -> None:
        result = sanitize_query('shop at No. 12, Jalan Ampang retail sector outlook')
        assert 'Jalan Ampang' not in result
        assert 'retail sector outlook' in result

    def test_sector_only_query_passes_through_unchanged(self) -> None:
        result = sanitize_query('F&B sector outlook Klang Valley 2026')
        assert result == 'F&B sector outlook Klang Valley 2026'


class TestRejection:
    def test_query_that_is_entirely_pii_is_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            sanitize_query('990101-14-5566')

    def test_empty_query_is_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            sanitize_query('   ')


class TestNameDetectorHook:
    def test_injected_name_detector_spans_are_removed(self) -> None:
        def fake_name_detector(text: str) -> list[tuple[int, int]]:
            start = text.index('Ali Bakery Sdn Bhd')
            return [(start, start + len('Ali Bakery Sdn Bhd'))]

        result = sanitize_query(
            'Ali Bakery Sdn Bhd F&B sector outlook',
            name_detector=fake_name_detector,
        )
        assert 'Ali Bakery Sdn Bhd' not in result
        assert 'F&B sector outlook' in result
