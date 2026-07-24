"""OCR tool — docs/architecture/06-tool-architecture.md §6.2's OCR row:

    Input: image/scanned PDF page, language hint
    Output: extracted text + per-region confidence + bounding boxes
    Permissions: Document Agent only
    Timeout: 30s/page
    Retries: 2, exponential backoff

Self-hosted (PaddleOCR/Tesseract) is the default engine per §6.2's note; a
cloud-OCR path is explicitly gated behind a document-sensitivity flag that
does not exist yet (Phase 11) — deliberately not implemented here rather
than shipped ungated. Sandboxing (§6.4 — OCR processes untrusted file
content) is a separate integration task; this module has a clean,
side-effect-free call boundary specifically so sandboxing can wrap it later
without a rewrite.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.schemas import (
    AuditSink,
    BoundingBox,
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
    log_tool_invocation,
)

TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 3  # first attempt + 2 retries, per §6.2's "Retries: 2"
ALLOWED_CALLERS = frozenset({'document_agent'})


class OCRRegion(BaseModel):
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bounding_box: BoundingBox


class OCRResult(BaseModel):
    page: int = Field(ge=1)
    text: str
    regions: list[OCRRegion] = Field(default_factory=list)


# An engine takes (image_bytes, language_hint, page) and returns the raw
# per-region OCR results for that one page. Swappable so a real
# PaddleOCR/Tesseract binding — or a test double — can be injected without
# changing run_ocr()'s retry/timeout/audit behavior.
OCREngine = Callable[[bytes, str, int], list[OCRRegion]]


def _default_engine(
    image_bytes: bytes, language_hint: str, page: int
) -> list[OCRRegion]:
    try:
        import pytesseract  # noqa: F401
    except ImportError as exc:
        raise ToolExternalServiceError(
            'No OCR engine is installed in this environment (pytesseract not '
            'found). Inject an `engine` callable, or install and wire a real '
            'self-hosted OCR engine before calling run_ocr() in production.'
        ) from exc
    # A real Tesseract/PaddleOCR binding is deliberately not implemented
    # here — see the module docstring. This branch exists so a `pytesseract`
    # install alone doesn't silently produce fabricated results.
    raise NotImplementedError(
        'pytesseract is installed but no engine implementation is wired yet '
        '— inject an `engine` callable rather than relying on the default.'
    )


@retry(
    retry=retry_if_exception_type((ToolTimeoutError, ToolExternalServiceError)),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _run_engine_with_timeout(
    engine: OCREngine, image_bytes: bytes, language_hint: str, page: int
) -> list[OCRRegion]:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(engine, image_bytes, language_hint, page)
        try:
            return future.result(timeout=TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            raise ToolTimeoutError(
                f'OCR did not complete within {TIMEOUT_SECONDS}s for page {page}'
            ) from exc
        except (ToolTimeoutError, ToolExternalServiceError):
            raise
        except Exception as exc:  # engine-internal failure, not ours to interpret
            raise ToolExternalServiceError(str(exc)) from exc


def run_ocr(
    image_bytes: bytes,
    language_hint: str,
    page: int,
    *,
    caller_agent: str,
    workflow_id: str | None = None,
    engine: OCREngine | None = None,
    audit_sink: AuditSink | None = None,
) -> OCRResult:
    """Run OCR on one image/scanned-PDF page. Raises ``ToolPermissionError``,
    ``ToolInputError``, ``ToolTimeoutError``, or ``ToolExternalServiceError``
    per docs/architecture/06-tool-architecture.md §6.1's typed error
    taxonomy — never a raw/library exception.
    """

    if caller_agent not in ALLOWED_CALLERS:
        raise ToolPermissionError(
            f"'{caller_agent}' is not permitted to call the OCR tool "
            f'(allowed: {sorted(ALLOWED_CALLERS)})'
        )
    if not image_bytes:
        raise ToolInputError('image_bytes must not be empty')
    if page < 1:
        raise ToolInputError(f'page must be >= 1, got {page}')

    input_hash = hashlib.sha256(image_bytes + language_hint.encode()).hexdigest()
    started = time.monotonic()
    active_engine = engine or _default_engine

    try:
        regions = _run_engine_with_timeout(
            active_engine, image_bytes, language_hint, page
        )
    except ToolTimeoutError as exc:
        _log(
            input_hash, None, started, 'timeout', caller_agent, workflow_id, audit_sink
        )
        raise exc
    except ToolExternalServiceError as exc:
        _log(
            input_hash,
            None,
            started,
            'external_error',
            caller_agent,
            workflow_id,
            audit_sink,
        )
        raise exc

    result = OCRResult(
        page=page, text='\n'.join(r.text for r in regions), regions=regions
    )
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
            tool_name='ocr',
            caller_agent=caller_agent,
            workflow_id=workflow_id,
            input_hash=input_hash,
            output_hash=output_hash,
            latency_ms=(time.monotonic() - started_at) * 1000,
            outcome=outcome,  # type: ignore[arg-type]
        ),
        sink=audit_sink,
    )
