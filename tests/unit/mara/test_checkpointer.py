"""Smoke tests for shared/workflow_engine/checkpointer — verifies that the
Postgres checkpointer context manager builds the correct DSN and delegates
to AsyncPostgresSaver correctly, without requiring a live Postgres instance.

docs/architecture/07-workflow-architecture.md §7.6, ACCB Condition C-5.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from shared.config.settings import Settings
from shared.workflow_engine.checkpointer import (
    ensure_checkpoint_schema,
    postgres_checkpointer,
)


@pytest.fixture(autouse=True)
def _dev_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('MARA_ENVIRONMENT', 'dev')


def test_postgres_checkpointer_yields_async_postgres_saver() -> None:
    """The context manager should yield an AsyncPostgresSaver instance
    connected to the correct DSN."""
    mock_saver = AsyncMock()
    mock_saver.__aenter__ = AsyncMock(return_value=mock_saver)
    mock_saver.__aexit__ = AsyncMock()

    with patch(
        'shared.workflow_engine.checkpointer.AsyncPostgresSaver.from_conn_string',
        return_value=mock_saver,
    ) as mock_from_conn:
        settings = Settings()

        async def _run() -> None:
            async with postgres_checkpointer(settings) as saver:
                assert saver is mock_saver

        import asyncio

        asyncio.run(_run())

        # Verify the DSN transformation: +asyncpg suffix removed
        called_dsn = mock_from_conn.call_args[0][0]
        assert '+asyncpg' not in called_dsn
        assert called_dsn.startswith('postgresql://')


def test_checkpointer_uses_primary_dsn_not_dify() -> None:
    """The checkpointer must connect to the *primary* Postgres, never Dify's
    instance — ACCB Condition C-5 (docs/architecture/09-knowledge-architecture.md
    §9.1.1)."""
    mock_saver = AsyncMock()
    mock_saver.__aenter__ = AsyncMock(return_value=mock_saver)
    mock_saver.__aexit__ = AsyncMock()

    with patch(
        'shared.workflow_engine.checkpointer.AsyncPostgresSaver.from_conn_string',
        return_value=mock_saver,
    ) as mock_from_conn:
        settings = Settings()

        async def _run() -> None:
            async with postgres_checkpointer(settings):
                pass

        import asyncio

        asyncio.run(_run())

        called_dsn = mock_from_conn.call_args[0][0]

        # Must use primary port (5432), not dify port (5433)
        assert '5432' in called_dsn or 'mara_platform' in called_dsn
        assert '5433' not in called_dsn or 'dify' not in called_dsn


def test_dsn_transformation_strips_asyncpg_driver() -> None:
    """The checkpointer must strip the '+asyncpg' driver suffix from the DSN
    because AsyncPostgresSaver expects a plain 'postgresql://' scheme."""
    mock_saver = AsyncMock()
    mock_saver.__aenter__ = AsyncMock(return_value=mock_saver)
    mock_saver.__aexit__ = AsyncMock()

    with patch(
        'shared.workflow_engine.checkpointer.AsyncPostgresSaver.from_conn_string',
        return_value=mock_saver,
    ) as mock_from_conn:
        settings = Settings()

        async def _run() -> None:
            async with postgres_checkpointer(settings):
                pass

        import asyncio

        asyncio.run(_run())

        called_dsn = mock_from_conn.call_args[0][0]
        assert called_dsn.startswith('postgresql://')
        assert called_dsn == str(settings.database.primary_dsn).replace(
            'postgresql+asyncpg://', 'postgresql://'
        )


def test_ensure_checkpoint_schema_calls_setup() -> None:
    """ensure_checkpoint_schema() should call saver.setup() exactly once."""
    mock_saver = AsyncMock()
    mock_saver.__aenter__ = AsyncMock(return_value=mock_saver)
    mock_saver.__aexit__ = AsyncMock()

    with patch(
        'shared.workflow_engine.checkpointer.AsyncPostgresSaver.from_conn_string',
        return_value=mock_saver,
    ):

        async def _run() -> None:
            settings = Settings()
            await ensure_checkpoint_schema(settings)

        import asyncio

        asyncio.run(_run())

        mock_saver.setup.assert_awaited_once()


def test_ensure_checkpoint_schema_is_idempotent() -> None:
    """Multiple calls to ensure_checkpoint_schema should be safe — setup()
    is documented as idempotent by langgraph-checkpoint-postgres."""
    mock_saver = AsyncMock()
    mock_saver.__aenter__ = AsyncMock(return_value=mock_saver)
    mock_saver.__aexit__ = AsyncMock()

    with patch(
        'shared.workflow_engine.checkpointer.AsyncPostgresSaver.from_conn_string',
        return_value=mock_saver,
    ):

        async def _run() -> None:
            settings = Settings()
            await ensure_checkpoint_schema(settings)
            await ensure_checkpoint_schema(settings)

        import asyncio

        asyncio.run(_run())

        # setup() should be called every time (it's idempotent internally)
        assert mock_saver.setup.await_count == 2
