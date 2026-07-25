"""RAG / knowledge query tool — docs/architecture/06-tool-architecture.md §6.2.

    Permissions: all 7 agents (derived from shared/agent_profiles/, per §6.7)
    Timeout: 10s
    Retries: 2, on timeout/external-service failure

Calls `services/knowledge_service` (Dify-backed, on its own database instance —
docs/architecture/09-knowledge-architecture.md §9.1.1), never Dify directly.

This is the first tool whose output an agent cites at scale, which makes it the
first place §6.1's citation-verification control actually bites: it records
every chunk it returned into the task's `ProvenanceLedger`, so an agent citing a
policy clause that was never retrieved is caught deterministically rather than
believed on the strength of being well-formed. Recording happens here, in the
tool, for the same reason invocation logging does — the record must exist even
if the agent's subsequent reasoning crashes.
"""

from __future__ import annotations

import asyncio
import hashlib
import time

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from services.knowledge_service.contract import (
    KnowledgeBackend,
    KnowledgeBackendNotConfiguredError,
    UnconfiguredBackend,
)
from shared.agent_profiles import callers_allowed_for_tool
from shared.provenance import ProvenanceLedger
from shared.schemas import (
    AuditSink,
    RetrievalQuery,
    RetrievalResult,
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
    log_tool_invocation,
)

TOOL_NAME = 'rag_query'
TIMEOUT_SECONDS = 10.0
MAX_ATTEMPTS = 3  # first attempt + 2 retries, per §6.2's "Retries: 2"
# Derived from the profile registry — see tools/ocr/ocr_tool.py for why.
ALLOWED_CALLERS = callers_allowed_for_tool(TOOL_NAME)


@retry(
    retry=retry_if_exception_type((ToolTimeoutError, ToolExternalServiceError)),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
async def _retrieve_with_timeout(
    backend: KnowledgeBackend, query: RetrievalQuery
) -> RetrievalResult:
    try:
        async with asyncio.timeout(TIMEOUT_SECONDS):
            return await backend.retrieve(query)
    except TimeoutError as exc:
        raise ToolTimeoutError(
            f'Knowledge retrieval did not complete within {TIMEOUT_SECONDS}s'
        ) from exc
    except KnowledgeBackendNotConfiguredError:
        # Deliberately not retried and not converted: a missing backend is a
        # deployment fault, and retrying it three times only delays the same
        # error while making the logs read like a flaky dependency.
        raise
    except (ToolTimeoutError, ToolExternalServiceError):
        raise
    except Exception as exc:
        raise ToolExternalServiceError(str(exc)) from exc


async def rag_query(
    query: RetrievalQuery,
    *,
    caller_agent: str,
    workflow_id: str | None = None,
    backend: KnowledgeBackend | None = None,
    ledger: ProvenanceLedger | None = None,
    audit_sink: AuditSink | None = None,
) -> RetrievalResult:
    """Retrieve knowledge chunks for ``query``.

    Raises ``ToolPermissionError``, ``ToolInputError``, ``ToolTimeoutError``, or
    ``ToolExternalServiceError`` per §6.1, and
    ``KnowledgeBackendNotConfiguredError`` when no corpus is wired up — the last
    of these deliberately distinct from an empty result, since "nothing was
    searched" and "nothing was found" license very different agent behavior
    (docs/architecture/05-agent-architecture.md §5.4).

    ``ledger`` is optional but omitting it has consequences worth stating: the
    task's citations then verify against an empty ledger, and
    ``ProvenanceLedger.verify`` fails closed, so every citation is rejected. That
    is the correct direction to fail — an unrecorded retrieval should not yield
    citations an officer is invited to trust — but it means a caller that
    intends to cite must pass one.
    """

    if caller_agent not in ALLOWED_CALLERS:
        raise ToolPermissionError(
            f"'{caller_agent}' is not permitted to call the RAG/knowledge "
            f'query tool (allowed: {sorted(ALLOWED_CALLERS)})'
        )
    if not query.query.strip():
        raise ToolInputError('query must not be blank')

    input_hash = hashlib.sha256(query.model_dump_json().encode()).hexdigest()
    started = time.monotonic()
    active_backend = backend or UnconfiguredBackend()

    try:
        result = await _retrieve_with_timeout(active_backend, query)
    except ToolTimeoutError:
        _log(
            input_hash, None, started, 'timeout', caller_agent, workflow_id, audit_sink
        )
        raise
    except (ToolExternalServiceError, KnowledgeBackendNotConfiguredError):
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

    # §6.1: record what was actually returned, before the caller can act on it.
    if ledger is not None:
        ledger.record_returned(TOOL_NAME, result.citable_refs())

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
            tool_name=TOOL_NAME,
            caller_agent=caller_agent,
            workflow_id=workflow_id,
            input_hash=input_hash,
            output_hash=output_hash,
            latency_ms=(time.monotonic() - started_at) * 1000,
            outcome=outcome,  # type: ignore[arg-type]
        ),
        sink=audit_sink,
    )
