"""PDF parse tool — docs/architecture/06-tool-architecture.md §6.2's
PDF-parse row:

    Input: PDF file
    Output: structured text/tables/metadata
    Permissions: Document Agent
    Timeout: 15s
    Retries: 2
    Notes: "Native text-layer extraction before falling back to OCR"

Native extraction uses ``pypdf`` (already a pinned OpenHands dependency —
no new package added for this). OCR fallback and table extraction both need
a page-image renderer / table-detection library this repo doesn't have
wired yet (see the ``page_image_renderer`` parameter below) — deliberately
left as an injectable seam with an honest "not wired" default rather than a
fabricated implementation, matching tools/ocr's same pattern.
"""

from __future__ import annotations

import hashlib
import io
import time
from collections.abc import Callable

from pydantic import BaseModel, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.schemas import (
    AuditSink,
    ExtractionSource,
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
    log_tool_invocation,
)
from tools.ocr.ocr_tool import OCREngine, run_ocr

TIMEOUT_SECONDS = 15.0
MAX_ATTEMPTS = 3  # first attempt + 2 retries, per §6.2's "Retries: 2"
ALLOWED_CALLERS = frozenset({'document_agent'})


class ParsedTable(BaseModel):
    page: int = Field(ge=1)
    rows: list[list[str]] = Field(default_factory=list)


class ParsedPage(BaseModel):
    page: int = Field(ge=1)
    text: str
    source: ExtractionSource
    tables: list[ParsedTable] = Field(default_factory=list)


class PDFParseResult(BaseModel):
    document_id: str
    pages: list[ParsedPage] = Field(default_factory=list)


# Renders one PDF page to an image (for the OCR fallback path). Not wired to
# a real implementation yet — see the module docstring. Injectable so a
# future task (or a test) can supply one without changing parse_pdf()'s
# control flow.
PageImageRenderer = Callable[[bytes, int], bytes]


@retry(
    retry=retry_if_exception_type((ToolTimeoutError, ToolExternalServiceError)),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _read_pdf(pdf_bytes: bytes) -> PdfReader:
    try:
        return PdfReader(io.BytesIO(pdf_bytes))
    except PdfReadError as exc:
        raise ToolInputError(f'Not a readable PDF: {exc}') from exc


def parse_pdf(
    pdf_bytes: bytes,
    document_id: str,
    *,
    caller_agent: str,
    workflow_id: str | None = None,
    page_image_renderer: PageImageRenderer | None = None,
    ocr_engine: OCREngine | None = None,
    audit_sink: AuditSink | None = None,
) -> PDFParseResult:
    """Parse a PDF: native text-layer extraction per page, falling back to
    OCR only for a page whose native text is empty, and only if a
    ``page_image_renderer`` is supplied. Raises the typed error taxonomy
    from docs/architecture/06-tool-architecture.md §6.1 — never a raw
    ``pypdf`` exception.
    """

    if caller_agent not in ALLOWED_CALLERS:
        raise ToolPermissionError(
            f"'{caller_agent}' is not permitted to call the PDF-parse tool "
            f'(allowed: {sorted(ALLOWED_CALLERS)})'
        )
    if not pdf_bytes:
        raise ToolInputError('pdf_bytes must not be empty')
    if not document_id:
        raise ToolInputError('document_id must not be empty')

    input_hash = hashlib.sha256(pdf_bytes).hexdigest()
    started = time.monotonic()

    try:
        reader = _read_pdf(pdf_bytes)
        pages: list[ParsedPage] = []
        for index, pdf_page in enumerate(reader.pages, start=1):
            text = (pdf_page.extract_text() or '').strip()
            source = ExtractionSource.PDF_TEXT_LAYER

            if not text and page_image_renderer is not None and ocr_engine is not None:
                image_bytes = page_image_renderer(pdf_bytes, index)
                ocr_result = run_ocr(
                    image_bytes,
                    language_hint='auto',
                    page=index,
                    caller_agent=caller_agent,
                    workflow_id=workflow_id,
                    engine=ocr_engine,
                    audit_sink=audit_sink,
                )
                text = ocr_result.text
                source = ExtractionSource.OCR

            pages.append(ParsedPage(page=index, text=text, source=source, tables=[]))
    except ToolInputError:
        _log(
            input_hash,
            None,
            started,
            'input_error',
            caller_agent,
            workflow_id,
            audit_sink,
        )
        raise
    except (ToolTimeoutError, ToolExternalServiceError) as exc:
        outcome = 'timeout' if isinstance(exc, ToolTimeoutError) else 'external_error'
        _log(input_hash, None, started, outcome, caller_agent, workflow_id, audit_sink)
        raise
    except Exception as exc:  # pypdf-internal failure not already typed above
        _log(
            input_hash,
            None,
            started,
            'external_error',
            caller_agent,
            workflow_id,
            audit_sink,
        )
        raise ToolExternalServiceError(str(exc)) from exc

    result = PDFParseResult(document_id=document_id, pages=pages)
    output_hash = hashlib.sha256(result.model_dump_json().encode()).hexdigest()
    _log(
        input_hash,
        output_hash,
        started,
        'success',
        caller_agent,
        workflow_id,
        audit_sink,
    )
    return result


def _log(
    input_hash: str,
    output_hash: str | None,
    started_at: float,
    outcome: str,
    caller_agent: str,
    workflow_id: str | None,
    audit_sink: AuditSink | None,
) -> None:
    log_tool_invocation(
        ToolInvocationLog(
            tool_name='pdf_parse',
            caller_agent=caller_agent,
            workflow_id=workflow_id,
            input_hash=input_hash,
            output_hash=output_hash,
            latency_ms=(time.monotonic() - started_at) * 1000,
            outcome=outcome,  # type: ignore[arg-type]
        ),
        sink=audit_sink,
    )
