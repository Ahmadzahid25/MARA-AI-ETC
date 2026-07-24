"""Unit tests for tools/documents/pdf_parse.py — uses real pypdf-generated
PDF bytes (pypdf is already a pinned dependency), not mocked PDF parsing,
so these tests exercise the actual native-text-layer extraction path."""

from __future__ import annotations

import io

import pytest
from pypdf import PdfWriter

from shared.schemas import ExtractionSource, ToolInputError, ToolPermissionError
from tools.documents.pdf_parse import parse_pdf
from tools.ocr.ocr_tool import OCRRegion


def _blank_pdf_bytes(num_pages: int = 2) -> bytes:
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


class TestPermissionAndInputValidation:
    def test_disallowed_caller_rejected(self) -> None:
        with pytest.raises(ToolPermissionError):
            parse_pdf(_blank_pdf_bytes(), 'doc-1', caller_agent='finance_agent')

    def test_empty_bytes_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            parse_pdf(b'', 'doc-1', caller_agent='document_agent')

    def test_empty_document_id_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            parse_pdf(_blank_pdf_bytes(), '', caller_agent='document_agent')

    def test_malformed_pdf_bytes_rejected(self) -> None:
        with pytest.raises(ToolInputError):
            parse_pdf(b'this is not a pdf', 'doc-1', caller_agent='document_agent')


class TestNativeTextExtraction:
    def test_real_pdf_is_parsed_page_by_page(self) -> None:
        result = parse_pdf(
            _blank_pdf_bytes(num_pages=3), 'doc-1', caller_agent='document_agent'
        )
        assert result.document_id == 'doc-1'
        assert len(result.pages) == 3
        assert [p.page for p in result.pages] == [1, 2, 3]

    def test_blank_page_without_ocr_fallback_wired_stays_native_with_empty_text(
        self,
    ) -> None:
        result = parse_pdf(
            _blank_pdf_bytes(num_pages=1), 'doc-1', caller_agent='document_agent'
        )
        page = result.pages[0]
        assert page.text == ''
        assert page.source == ExtractionSource.PDF_TEXT_LAYER

    def test_audit_sink_receives_success_entry(self) -> None:
        captured = []
        parse_pdf(
            _blank_pdf_bytes(num_pages=1),
            'doc-1',
            caller_agent='document_agent',
            audit_sink=captured.append,
        )
        assert len(captured) == 1
        assert captured[0].tool_name == 'pdf_parse'
        assert captured[0].outcome == 'success'


class TestOCRFallback:
    def test_blank_page_falls_back_to_ocr_when_renderer_and_engine_supplied(
        self,
    ) -> None:
        renderer_calls = []

        def renderer(pdf_bytes: bytes, page: int) -> bytes:
            renderer_calls.append(page)
            return b'fake-page-image'

        def engine(
            image_bytes: bytes, language_hint: str, page: int
        ) -> list[OCRRegion]:
            from shared.schemas import BoundingBox

            return [
                OCRRegion(
                    text='ocr recovered text',
                    confidence=0.7,
                    bounding_box=BoundingBox(page=page, x=0, y=0, width=1, height=1),
                )
            ]

        result = parse_pdf(
            _blank_pdf_bytes(num_pages=1),
            'doc-1',
            caller_agent='document_agent',
            page_image_renderer=renderer,
            ocr_engine=engine,
        )
        page = result.pages[0]
        assert page.text == 'ocr recovered text'
        assert page.source == ExtractionSource.OCR
        assert renderer_calls == [1]
