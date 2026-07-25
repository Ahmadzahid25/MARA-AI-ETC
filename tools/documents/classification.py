"""Document classification tool — docs/architecture/06-tool-architecture.md
§6.2's document-classification row:

    Input: Document file
    Output: Document type label + confidence
    Permissions: Document Agent
    Timeout: 10s
    Retries: 2

"Feeds routing decisions in the Document Assessment workflow" (§6.2) — that
workflow doesn't exist yet (see apps/officer-workspace/AGENTS.md-adjacent
note: Milestone 1's workflow task is blocked on resolving whether it
includes a Compliance step). This tool is implemented standalone so it's
ready when that workflow is built.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.agent_profiles import callers_allowed_for_tool
from shared.schemas import (
    AuditSink,
    DocumentClassification,
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
    log_tool_invocation,
)

TOOL_NAME = 'document_classification'
TIMEOUT_SECONDS = 10.0
MAX_ATTEMPTS = 3  # first attempt + 2 retries, per §6.2's "Retries: 2"
# Derived from the profile registry — see tools/ocr/ocr_tool.py for why.
ALLOWED_CALLERS = callers_allowed_for_tool(TOOL_NAME)

# Returns (document_type, confidence) for one document. Swappable so a real
# classifier model can be injected without changing classify_document()'s
# retry/timeout/audit behavior.
Classifier = Callable[[bytes], tuple[str, float]]


def _default_classifier(file_bytes: bytes) -> tuple[str, float]:
    raise ToolExternalServiceError(
        'No document classifier is wired in this environment. Inject a '
        "`classifier` callable — the real model choice (and MARA's actual "
        'document-type taxonomy, per shared/schemas/documents.py) is not '
        'decided yet.'
    )


@retry(
    retry=retry_if_exception_type((ToolTimeoutError, ToolExternalServiceError)),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _run_classifier_with_timeout(
    classifier: Classifier, file_bytes: bytes
) -> tuple[str, float]:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(classifier, file_bytes)
        try:
            return future.result(timeout=TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            raise ToolTimeoutError(
                f'Classification did not complete within {TIMEOUT_SECONDS}s'
            ) from exc
        except (ToolTimeoutError, ToolExternalServiceError):
            raise
        except Exception as exc:
            raise ToolExternalServiceError(str(exc)) from exc


def classify_document(
    file_bytes: bytes,
    *,
    caller_agent: str,
    workflow_id: str | None = None,
    classifier: Classifier | None = None,
    audit_sink: AuditSink | None = None,
) -> DocumentClassification:
    """Classify a document's type. Raises ``ToolPermissionError``,
    ``ToolInputError``, ``ToolTimeoutError``, or ``ToolExternalServiceError``
    per docs/architecture/06-tool-architecture.md §6.1.
    """

    if caller_agent not in ALLOWED_CALLERS:
        raise ToolPermissionError(
            f"'{caller_agent}' is not permitted to call the document "
            f'classification tool (allowed: {sorted(ALLOWED_CALLERS)})'
        )
    if not file_bytes:
        raise ToolInputError('file_bytes must not be empty')

    input_hash = hashlib.sha256(file_bytes).hexdigest()
    started = time.monotonic()
    active_classifier = classifier or _default_classifier

    try:
        document_type, confidence = _run_classifier_with_timeout(
            active_classifier, file_bytes
        )
    except ToolTimeoutError:
        _log(
            input_hash, None, started, 'timeout', caller_agent, workflow_id, audit_sink
        )
        raise
    except ToolExternalServiceError:
        _log(
            input_hash,
            None,
            started,
            'external_error',
            caller_agent,
            workflow_id,
            audit_sink,
        )
        raise

    result = DocumentClassification(document_type=document_type, confidence=confidence)
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
            tool_name='document_classification',
            caller_agent=caller_agent,
            workflow_id=workflow_id,
            input_hash=input_hash,
            output_hash=output_hash,
            latency_ms=(time.monotonic() - started_at) * 1000,
            outcome=outcome,  # type: ignore[arg-type]
        ),
        sink=audit_sink,
    )
