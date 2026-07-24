"""Unit tests for agents/document_agent/document_agent.py."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock

import pytest
from pypdf import PdfWriter

from agents.document_agent.document_agent import (
    DocumentAgent,
    ExtractionParsingError,
    _parse_llm_fields,
)
from shared.schemas import ToolInputError
from shared.schemas.documents import ExtractionSource
from tools.documents.pdf_parse import ParsedPage


def _blank_pdf_bytes(num_pages: int = 1) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _pages() -> list[ParsedPage]:
    return [
        ParsedPage(
            page=1, text='Name: Ali bin Ahmad', source=ExtractionSource.PDF_TEXT_LAYER
        )
    ]


class TestParseLLMFields:
    def test_valid_json_produces_extracted_fields(self) -> None:
        raw = (
            '[{"name": "applicant_name", "value": "Ali bin Ahmad", '
            '"confidence": 0.95, "page": 1}]'
        )
        fields = _parse_llm_fields(raw, 'doc-1', _pages())
        assert len(fields) == 1
        assert fields[0].name == 'applicant_name'
        assert fields[0].source == ExtractionSource.PDF_TEXT_LAYER
        assert fields[0].citation.document_id == 'doc-1'
        assert fields[0].citation.page == 1

    def test_invalid_json_raises_extraction_parsing_error(self) -> None:
        with pytest.raises(ExtractionParsingError):
            _parse_llm_fields('not json at all', 'doc-1', _pages())

    def test_non_array_json_raises(self) -> None:
        with pytest.raises(ExtractionParsingError):
            _parse_llm_fields('{"name": "x"}', 'doc-1', _pages())

    def test_missing_required_key_raises(self) -> None:
        with pytest.raises(ExtractionParsingError):
            _parse_llm_fields('[{"name": "x", "value": "y"}]', 'doc-1', _pages())

    def test_confidence_out_of_range_raises(self) -> None:
        raw = '[{"name": "x", "value": "y", "confidence": 1.5, "page": 1}]'
        with pytest.raises(Exception):  # noqa: B017 - pydantic ValidationError
            _parse_llm_fields(raw, 'doc-1', _pages())

    def test_page_not_among_parsed_pages_raises(self) -> None:
        raw = '[{"name": "x", "value": "y", "confidence": 0.9, "page": 99}]'
        with pytest.raises(ExtractionParsingError):
            _parse_llm_fields(raw, 'doc-1', _pages())


class TestDocumentAgentProcessDocument:
    @pytest.mark.asyncio
    async def test_uses_injected_field_extractor(self) -> None:
        async def fake_extractor(pages, classification):
            from shared.schemas.documents import Citation, ExtractedField

            return [
                ExtractedField(
                    name='applicant_name',
                    value='Ali bin Ahmad',
                    confidence=0.9,
                    source=ExtractionSource.PDF_TEXT_LAYER,
                    citation=Citation(document_id='doc-1', page=1),
                )
            ]

        agent = DocumentAgent(
            field_extractor=fake_extractor,
            classifier=lambda _b: ('bank_statement', 0.9),
        )
        record = await agent.process_document('doc-1', _blank_pdf_bytes())

        assert record.document_id == 'doc-1'
        assert len(record.fields) == 1
        assert record.fields[0].name == 'applicant_name'

    @pytest.mark.asyncio
    async def test_low_confidence_field_is_flagged_not_dropped(self) -> None:
        async def fake_extractor(pages, classification):
            from shared.schemas.documents import Citation, ExtractedField

            return [
                ExtractedField(
                    name='blurry_field',
                    value='maybe-42',
                    confidence=0.4,
                    source=ExtractionSource.OCR,
                    citation=Citation(document_id='doc-1', page=1),
                )
            ]

        agent = DocumentAgent(
            field_extractor=fake_extractor,
            classifier=lambda _b: ('bank_statement', 0.9),
        )
        record = await agent.process_document('doc-1', _blank_pdf_bytes())

        assert (
            len(record.low_confidence_fields(threshold=agent.confidence_threshold)) == 1
        )

    @pytest.mark.asyncio
    async def test_malformed_pdf_propagates_tool_input_error(self) -> None:
        agent = DocumentAgent(
            field_extractor=AsyncMock(return_value=[]),
            classifier=lambda _b: ('bank_statement', 0.9),
        )
        with pytest.raises(ToolInputError):
            await agent.process_document('doc-1', b'not a pdf')

    @pytest.mark.asyncio
    async def test_default_extractor_calls_llm_client_with_document_tier(self) -> None:
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=(
                        '[{"name": "n", "value": "v", "confidence": 0.9, "page": 1}]'
                    )
                )
            )
        ]
        mock_llm = MagicMock()
        mock_llm.complete_for_agent = AsyncMock(return_value=mock_response)

        agent = DocumentAgent(
            llm_client=mock_llm, classifier=lambda _b: ('bank_statement', 0.9)
        )
        record = await agent.process_document('doc-1', _blank_pdf_bytes())

        assert len(record.fields) == 1
        mock_llm.complete_for_agent.assert_awaited_once()
        called_agent = mock_llm.complete_for_agent.call_args[0][0]
        assert called_agent.value == 'document_agent'
