"""Unit tests for services/audit_service — mocks asyncpg at the pool
boundary (no live Postgres in this environment; dev-3's infrastructure
verification pass, per infrastructure/AGENTS.md, is what proves this
against a real database)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from services.audit_service.adapters import approval_record_to_audit_event
from services.audit_service.audit_service import (
    AuditEvent,
    AuditQueryFilters,
    audit_pool,
    query_audit_events,
    write_audit_event,
)
from shared.config.settings import Settings
from shared.schemas.approval import ApprovalAction, ApprovalRecord, FieldCorrection


class TestAuditPool:
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

        import services.audit_service.audit_service as mod

        monkeypatch.setattr(mod.asyncpg, 'create_pool', fake_create_pool)

        settings = Settings()
        async with audit_pool(settings) as pool:
            assert pool is not None

        assert '+asyncpg' not in captured_dsn['dsn']
        assert captured_dsn['dsn'].startswith('postgresql://')

    @pytest.mark.asyncio
    async def test_closes_pool_on_exit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv('MARA_ENVIRONMENT', 'dev')
        mock_pool = MagicMock()
        mock_pool.close = AsyncMock()

        async def fake_create_pool(dsn: str):
            return mock_pool

        import services.audit_service.audit_service as mod

        monkeypatch.setattr(mod.asyncpg, 'create_pool', fake_create_pool)

        settings = Settings()
        async with audit_pool(settings):
            pass

        mock_pool.close.assert_awaited_once()


class TestWriteAuditEvent:
    @pytest.mark.asyncio
    async def test_inserts_with_expected_columns(self) -> None:
        pool = MagicMock()
        pool.execute = AsyncMock()
        event = AuditEvent(
            workflow_id='wf-1',
            actor_id='officer-1',
            actor_role='officer',
            event_type='approval',
            payload={'document_id': 'doc-1'},
        )

        await write_audit_event(pool, event)

        pool.execute.assert_awaited_once()
        args = pool.execute.call_args[0]
        assert 'INSERT INTO audit_memory' in args[0]
        assert args[1:] == (
            'wf-1',
            'officer-1',
            'officer',
            'hq',  # branch_code — AuditEvent default (docs/architecture/
            # 18-per-branch-database-schema.md §3 Jadual 8)
            'approval',
            '{"document_id": "doc-1"}',
        )


class TestQueryAuditEvents:
    @pytest.mark.asyncio
    async def test_no_filters_queries_without_where_clause(self) -> None:
        pool = MagicMock()
        pool.fetch = AsyncMock(return_value=[])

        await query_audit_events(pool, AuditQueryFilters())

        query = pool.fetch.call_args[0][0]
        assert 'WHERE' not in query

    @pytest.mark.asyncio
    async def test_workflow_id_filter_adds_where_clause(self) -> None:
        pool = MagicMock()
        pool.fetch = AsyncMock(return_value=[])

        await query_audit_events(pool, AuditQueryFilters(workflow_id='wf-1'))

        args = pool.fetch.call_args[0]
        assert 'workflow_id = $1' in args[0]
        assert args[1] == 'wf-1'

    @pytest.mark.asyncio
    async def test_multiple_filters_combine_with_and(self) -> None:
        pool = MagicMock()
        pool.fetch = AsyncMock(return_value=[])

        await query_audit_events(
            pool, AuditQueryFilters(workflow_id='wf-1', actor_id='officer-1')
        )

        query = pool.fetch.call_args[0][0]
        assert 'workflow_id = $1 AND actor_id = $2' in query

    @pytest.mark.asyncio
    async def test_rows_are_parsed_into_audit_events(self) -> None:
        pool = MagicMock()
        pool.fetch = AsyncMock(
            return_value=[
                {
                    'id': 1,
                    'occurred_at': datetime(2026, 1, 1, tzinfo=UTC),
                    'workflow_id': 'wf-1',
                    'actor_id': 'officer-1',
                    'actor_role': 'officer',
                    'event_type': 'approval',
                    'payload': '{"document_id": "doc-1"}',
                }
            ]
        )

        results = await query_audit_events(pool, AuditQueryFilters())

        assert len(results) == 1
        assert results[0].id == 1
        assert results[0].payload == {'document_id': 'doc-1'}

    @pytest.mark.asyncio
    async def test_limit_defaults_to_100(self) -> None:
        pool = MagicMock()
        pool.fetch = AsyncMock(return_value=[])

        await query_audit_events(pool, AuditQueryFilters())

        assert pool.fetch.call_args[0][-1] == 100


class TestApprovalRecordToAuditEvent:
    def _record(
        self, action: ApprovalAction, corrections: list | None = None
    ) -> ApprovalRecord:
        return ApprovalRecord(
            workflow_thread_id='wf-1',
            document_id='doc-1',
            action=action,
            actor='officer-1',
            reason='blurry',
            corrections=corrections or [],
        )

    def test_approve_maps_to_approval_event_type(self) -> None:
        event = approval_record_to_audit_event(self._record(ApprovalAction.APPROVE))
        assert event.event_type == 'approval'
        assert event.actor_id == 'officer-1'
        assert event.actor_role == 'officer'
        assert event.workflow_id == 'wf-1'

    def test_reject_maps_to_rejection_event_type(self) -> None:
        event = approval_record_to_audit_event(self._record(ApprovalAction.REJECT))
        assert event.event_type == 'rejection'

    def test_correct_maps_to_correction_event_type_with_corrections_in_payload(
        self,
    ) -> None:
        record = self._record(
            ApprovalAction.CORRECT,
            corrections=[
                FieldCorrection(field_name='applicant_name', corrected_value='Ali')
            ],
        )
        event = approval_record_to_audit_event(record)
        assert event.event_type == 'correction'
        assert event.payload['corrections'] == [
            {'field_name': 'applicant_name', 'corrected_value': 'Ali', 'reason': ''}
        ]
