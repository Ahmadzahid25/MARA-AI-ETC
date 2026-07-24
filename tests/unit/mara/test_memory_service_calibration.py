"""Unit tests for services/memory_service — mocks asyncpg at the pool
boundary (no live Postgres in this environment; dev-3's infrastructure
verification pass, per infrastructure/AGENTS.md item 8, is what proves
this against a real database once the table exists)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.memory_service.adapters import extraction_record_to_calibration_events
from services.memory_service.calibration import (
    CalibrationEvent,
    CalibrationStats,
    calibration_pool,
    query_calibration_stats,
    write_calibration_event,
)
from shared.config.settings import Settings
from shared.schemas.documents import (
    Citation,
    DocumentClassification,
    DocumentExtractionRecord,
    ExtractedField,
    ExtractionSource,
)


def _field(name: str, confidence: float) -> ExtractedField:
    return ExtractedField(
        name=name,
        value='v',
        confidence=confidence,
        source=ExtractionSource.PDF_TEXT_LAYER,
        citation=Citation(document_id='doc-1', page=1),
    )


class TestCalibrationPool:
    @pytest.mark.asyncio
    async def test_strips_asyncpg_driver_suffix_from_dsn(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv('MARA_ENVIRONMENT', 'dev')
        captured_dsn = {}

        async def fake_create_pool(dsn: str):
            captured_dsn['dsn'] = dsn
            mock_pool = MagicMock()
            mock_pool.close = AsyncMock()
            return mock_pool

        import services.memory_service.calibration as mod

        monkeypatch.setattr(mod.asyncpg, 'create_pool', fake_create_pool)

        settings = Settings()
        async with calibration_pool(settings) as pool:
            assert pool is not None

        assert '+asyncpg' not in captured_dsn['dsn']
        assert captured_dsn['dsn'].startswith('postgresql://')


class TestWriteCalibrationEvent:
    @pytest.mark.asyncio
    async def test_inserts_with_expected_columns(self) -> None:
        pool = MagicMock()
        pool.execute = AsyncMock()
        event = CalibrationEvent(
            agent_name='document_agent',
            workflow_id='wf-1',
            field_name='applicant_name',
            document_type='bank_statement',
            stated_confidence=0.6,
            was_corrected=True,
        )

        await write_calibration_event(pool, event)

        pool.execute.assert_awaited_once()
        args = pool.execute.call_args[0]
        assert 'INSERT INTO long_term_memory_calibration' in args[0]
        assert args[1:] == (
            'document_agent',
            'wf-1',
            'applicant_name',
            'bank_statement',
            0.6,
            True,
        )

    @pytest.mark.asyncio
    async def test_confidence_out_of_range_rejected(self) -> None:
        with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
            CalibrationEvent(
                agent_name='document_agent',
                field_name='x',
                stated_confidence=1.5,
                was_corrected=False,
            )


class TestQueryCalibrationStats:
    @pytest.mark.asyncio
    async def test_queries_by_agent_name_only_by_default(self) -> None:
        pool = MagicMock()
        pool.fetchrow = AsyncMock(
            return_value={
                'total_events': 10,
                'corrected_events': 3,
                'average_stated_confidence': 0.82,
                'average_confidence_when_corrected': 0.7,
            }
        )

        stats = await query_calibration_stats(pool, 'document_agent')

        args = pool.fetchrow.call_args[0]
        assert 'field_name' not in args[0]
        assert args[1] == 'document_agent'
        assert stats.total_events == 10
        assert stats.corrected_events == 3
        assert stats.correction_rate == pytest.approx(0.3)

    @pytest.mark.asyncio
    async def test_narrows_by_field_name_when_given(self) -> None:
        pool = MagicMock()
        pool.fetchrow = AsyncMock(
            return_value={
                'total_events': 5,
                'corrected_events': 5,
                'average_stated_confidence': 0.9,
                'average_confidence_when_corrected': 0.9,
            }
        )

        await query_calibration_stats(
            pool, 'document_agent', field_name='applicant_name'
        )

        query, *params = pool.fetchrow.call_args[0]
        assert 'field_name = $2' in query
        assert params == ['document_agent', 'applicant_name']

    def test_correction_rate_is_none_when_no_events(self) -> None:
        stats = CalibrationStats(
            agent_name='document_agent',
            field_name=None,
            total_events=0,
            corrected_events=0,
            average_stated_confidence=None,
            average_confidence_when_corrected=None,
        )
        assert stats.correction_rate is None

    def test_correction_rate_is_zero_when_nothing_corrected(self) -> None:
        stats = CalibrationStats(
            agent_name='document_agent',
            field_name=None,
            total_events=4,
            corrected_events=0,
            average_stated_confidence=0.95,
            average_confidence_when_corrected=None,
        )
        assert stats.correction_rate == 0.0


class TestExtractionRecordToCalibrationEvents:
    def _record(self) -> DocumentExtractionRecord:
        return DocumentExtractionRecord(
            document_id='doc-1',
            classification=DocumentClassification(
                document_type='bank_statement', confidence=0.95
            ),
            fields=[_field('applicant_name', 0.6), _field('account_number', 0.92)],
        )

    def test_every_field_produces_one_event(self) -> None:
        events = extraction_record_to_calibration_events(
            self._record(),
            agent_name='document_agent',
            workflow_id='wf-1',
            corrected_field_names=set(),
        )
        assert len(events) == 2
        assert {e.field_name for e in events} == {'applicant_name', 'account_number'}

    def test_corrected_field_names_flag_was_corrected(self) -> None:
        events = extraction_record_to_calibration_events(
            self._record(),
            agent_name='document_agent',
            workflow_id='wf-1',
            corrected_field_names={'applicant_name'},
        )
        by_name = {e.field_name: e for e in events}
        assert by_name['applicant_name'].was_corrected is True
        assert by_name['account_number'].was_corrected is False

    def test_document_type_carried_from_classification(self) -> None:
        events = extraction_record_to_calibration_events(
            self._record(),
            agent_name='document_agent',
            workflow_id='wf-1',
            corrected_field_names=set(),
        )
        assert all(e.document_type == 'bank_statement' for e in events)
