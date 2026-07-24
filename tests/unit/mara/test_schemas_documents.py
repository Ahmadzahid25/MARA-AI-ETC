"""Unit tests for shared/schemas/documents.py — the extraction contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from shared.schemas.documents import (
    BoundingBox,
    Citation,
    DocumentClassification,
    DocumentExtractionRecord,
    ExtractedField,
    ExtractionSource,
)


def _field(name: str, confidence: float) -> ExtractedField:
    return ExtractedField(
        name=name,
        value='some-value',
        confidence=confidence,
        source=ExtractionSource.OCR,
        citation=Citation(document_id='doc-1', page=1),
    )


class TestBoundingBox:
    def test_valid_bounding_box(self) -> None:
        box = BoundingBox(page=1, x=0, y=0, width=10, height=10)
        assert box.page == 1

    def test_page_must_be_at_least_one(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(page=0, x=0, y=0, width=10, height=10)

    def test_width_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            BoundingBox(page=1, x=0, y=0, width=0, height=10)


class TestCitation:
    def test_bounding_box_is_optional(self) -> None:
        citation = Citation(document_id='doc-1', page=2)
        assert citation.bounding_box is None

    def test_document_id_required(self) -> None:
        with pytest.raises(ValidationError):
            Citation(document_id='', page=1)


class TestExtractedField:
    def test_confidence_in_range_accepted(self) -> None:
        field = _field('name', 0.85)
        assert field.confidence == 0.85

    @pytest.mark.parametrize('bad_confidence', [-0.01, 1.01, 2.0, -1.0])
    def test_confidence_out_of_range_rejected(self, bad_confidence: float) -> None:
        with pytest.raises(ValidationError):
            _field('name', bad_confidence)

    def test_boundary_confidences_accepted(self) -> None:
        assert _field('name', 0.0).confidence == 0.0
        assert _field('name', 1.0).confidence == 1.0


class TestDocumentClassification:
    @pytest.mark.parametrize('bad_confidence', [-0.5, 1.5])
    def test_confidence_out_of_range_rejected(self, bad_confidence: float) -> None:
        with pytest.raises(ValidationError):
            DocumentClassification(
                document_type='bank_statement', confidence=bad_confidence
            )


class TestDocumentExtractionRecord:
    def test_low_confidence_fields_uses_default_threshold(self) -> None:
        record = DocumentExtractionRecord(
            document_id='doc-1',
            classification=DocumentClassification(
                document_type='bank_statement', confidence=0.95
            ),
            fields=[_field('a', 0.9), _field('b', 0.5), _field('c', 0.85)],
        )
        low = record.low_confidence_fields()
        assert {f.name for f in low} == {'b'}

    def test_low_confidence_fields_respects_custom_threshold(self) -> None:
        record = DocumentExtractionRecord(
            document_id='doc-1',
            classification=DocumentClassification(
                document_type='bank_statement', confidence=0.95
            ),
            fields=[_field('a', 0.9), _field('b', 0.5)],
        )
        assert {f.name for f in record.low_confidence_fields(threshold=0.95)} == {
            'a',
            'b',
        }

    def test_empty_fields_list_is_valid(self) -> None:
        record = DocumentExtractionRecord(
            document_id='doc-1',
            classification=DocumentClassification(
                document_type='unknown', confidence=0.3
            ),
        )
        assert record.fields == []
        assert record.low_confidence_fields() == []
