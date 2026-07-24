"""Unit tests for shared/schemas/tooling.py — the tool error taxonomy and
audit-log shape."""

from __future__ import annotations

import logging

import pytest
from pydantic import ValidationError

from shared.schemas.tooling import (
    ToolError,
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
    log_tool_invocation,
)


class TestErrorTaxonomy:
    @pytest.mark.parametrize(
        'error_cls',
        [
            ToolInputError,
            ToolTimeoutError,
            ToolExternalServiceError,
            ToolPermissionError,
        ],
    )
    def test_all_typed_errors_are_tool_errors(self, error_cls: type[ToolError]) -> None:
        assert issubclass(error_cls, ToolError)
        assert issubclass(error_cls, Exception)

    def test_typed_errors_carry_a_message(self) -> None:
        with pytest.raises(ToolInputError, match='bad input'):
            raise ToolInputError('bad input')


class TestToolInvocationLog:
    def test_valid_log_entry(self) -> None:
        entry = ToolInvocationLog(
            tool_name='ocr',
            caller_agent='document_agent',
            workflow_id='wf-1',
            input_hash='abc',
            output_hash='def',
            latency_ms=12.5,
            outcome='success',
        )
        assert entry.outcome == 'success'
        assert entry.timestamp is not None

    def test_workflow_id_is_optional(self) -> None:
        entry = ToolInvocationLog(
            tool_name='ocr',
            caller_agent='document_agent',
            input_hash='abc',
            latency_ms=1.0,
            outcome='success',
        )
        assert entry.workflow_id is None

    def test_negative_latency_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ToolInvocationLog(
                tool_name='ocr',
                caller_agent='document_agent',
                input_hash='abc',
                latency_ms=-1.0,
                outcome='success',
            )

    def test_invalid_outcome_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ToolInvocationLog(
                tool_name='ocr',
                caller_agent='document_agent',
                input_hash='abc',
                latency_ms=1.0,
                outcome='not-a-real-outcome',
            )


class TestLogToolInvocation:
    def _entry(self) -> ToolInvocationLog:
        return ToolInvocationLog(
            tool_name='ocr',
            caller_agent='document_agent',
            input_hash='abc',
            latency_ms=1.0,
            outcome='success',
        )

    def test_injected_sink_is_called_with_the_entry(self) -> None:
        captured: list[ToolInvocationLog] = []
        entry = self._entry()

        log_tool_invocation(entry, sink=captured.append)

        assert captured == [entry]

    def test_default_sink_logs_without_raising(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.INFO, logger='mara.tool_audit'):
            log_tool_invocation(self._entry())

        assert any('tool_invocation' in record.message for record in caplog.records)
