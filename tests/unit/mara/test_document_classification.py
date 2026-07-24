"""Unit tests for tools/documents/classification.py."""

from __future__ import annotations

import time

import pytest

from shared.schemas import (
    ToolExternalServiceError,
    ToolInputError,
    ToolPermissionError,
    ToolTimeoutError,
)
from tools.documents import classification as classification_module
from tools.documents.classification import classify_document


class TestPermissionAndInputValidation:
    def test_disallowed_caller_rejected(self) -> None:
        with pytest.raises(ToolPermissionError):
            classify_document(
                b'file-bytes',
                caller_agent='finance_agent',
                classifier=lambda _b: ('bank_statement', 0.9),
            )

    def test_empty_bytes_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            classify_document(b'', caller_agent='document_agent')


class TestSuccessfulRun:
    def test_returns_classification_from_injected_classifier(self) -> None:
        result = classify_document(
            b'file-bytes',
            caller_agent='document_agent',
            classifier=lambda _b: ('business_registration', 0.92),
        )
        assert result.document_type == 'business_registration'
        assert result.confidence == 0.92

    def test_audit_sink_receives_success_entry(self) -> None:
        captured = []
        classify_document(
            b'file-bytes',
            caller_agent='document_agent',
            classifier=lambda _b: ('bank_statement', 0.8),
            audit_sink=captured.append,
        )
        assert len(captured) == 1
        assert captured[0].tool_name == 'document_classification'
        assert captured[0].outcome == 'success'


class TestErrorPaths:
    def test_classifier_exception_becomes_external_service_error(self) -> None:
        def failing(_b: bytes) -> tuple[str, float]:
            raise RuntimeError('model unavailable')

        with pytest.raises(ToolExternalServiceError):
            classify_document(
                b'file-bytes', caller_agent='document_agent', classifier=failing
            )

    def test_timeout_raises_and_is_audited(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(classification_module, 'TIMEOUT_SECONDS', 0.05)

        def slow(_b: bytes) -> tuple[str, float]:
            time.sleep(1)
            return ('bank_statement', 0.9)

        captured = []
        with pytest.raises(ToolTimeoutError):
            classify_document(
                b'file-bytes',
                caller_agent='document_agent',
                classifier=slow,
                audit_sink=captured.append,
            )
        assert captured[-1].outcome == 'timeout'

    def test_default_classifier_raises_external_service_error(self) -> None:
        with pytest.raises(ToolExternalServiceError):
            classify_document(b'file-bytes', caller_agent='document_agent')
