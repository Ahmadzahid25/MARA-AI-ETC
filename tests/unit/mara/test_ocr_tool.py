"""Unit tests for tools/ocr/ocr_tool.py."""

from __future__ import annotations

import time

import pytest

from shared.schemas import (
    BoundingBox,
    ToolExternalServiceError,
    ToolInputError,
    ToolPermissionError,
    ToolTimeoutError,
)
from tools.ocr import ocr_tool
from tools.ocr.ocr_tool import OCRRegion, run_ocr


def _region(text: str = 'hello', confidence: float = 0.9) -> OCRRegion:
    return OCRRegion(
        text=text,
        confidence=confidence,
        bounding_box=BoundingBox(page=1, x=0, y=0, width=10, height=10),
    )


class TestPermissionAndInputValidation:
    def test_disallowed_caller_rejected(self) -> None:
        with pytest.raises(ToolPermissionError):
            run_ocr(
                b'fake-image-bytes',
                'en',
                1,
                caller_agent='finance_agent',
                engine=lambda *_: [_region()],
            )

    def test_empty_image_bytes_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            run_ocr(b'', 'en', 1, caller_agent='document_agent', engine=lambda *_: [])

    def test_invalid_page_number_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            run_ocr(
                b'fake-image-bytes',
                'en',
                0,
                caller_agent='document_agent',
                engine=lambda *_: [],
            )


class TestSuccessfulRun:
    def test_returns_assembled_result(self) -> None:
        result = run_ocr(
            b'fake-image-bytes',
            'en',
            3,
            caller_agent='document_agent',
            engine=lambda *_: [_region('line one'), _region('line two')],
        )
        assert result.page == 3
        assert result.text == 'line one\nline two'
        assert len(result.regions) == 2

    def test_audit_sink_receives_success_entry(self) -> None:
        captured = []
        run_ocr(
            b'fake-image-bytes',
            'en',
            1,
            caller_agent='document_agent',
            engine=lambda *_: [_region()],
            audit_sink=captured.append,
        )
        assert len(captured) == 1
        entry = captured[0]
        assert entry.tool_name == 'ocr'
        assert entry.caller_agent == 'document_agent'
        assert entry.outcome == 'success'
        assert entry.output_hash is not None


class TestErrorPaths:
    def test_engine_exception_becomes_external_service_error(self) -> None:
        def failing_engine(*_args: object) -> list[OCRRegion]:
            raise RuntimeError('engine exploded')

        with pytest.raises(ToolExternalServiceError):
            run_ocr(b'x', 'en', 1, caller_agent='document_agent', engine=failing_engine)

    def test_timeout_raises_and_is_audited(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(ocr_tool, 'TIMEOUT_SECONDS', 0.05)

        def slow_engine(*_args: object) -> list[OCRRegion]:
            time.sleep(1)
            return [_region()]

        captured = []
        with pytest.raises(ToolTimeoutError):
            run_ocr(
                b'x',
                'en',
                1,
                caller_agent='document_agent',
                engine=slow_engine,
                audit_sink=captured.append,
            )
        assert captured[-1].outcome == 'timeout'

    def test_transient_failure_then_success_is_retried(self) -> None:
        attempts = {'count': 0}

        def flaky_engine(*_args: object) -> list[OCRRegion]:
            attempts['count'] += 1
            if attempts['count'] < 2:
                raise RuntimeError('transient')
            return [_region()]

        result = run_ocr(
            b'x', 'en', 1, caller_agent='document_agent', engine=flaky_engine
        )
        assert attempts['count'] == 2
        assert len(result.regions) == 1

    def test_default_engine_without_pytesseract_raises_external_service_error(
        self,
    ) -> None:
        with pytest.raises(ToolExternalServiceError):
            run_ocr(b'x', 'en', 1, caller_agent='document_agent')
