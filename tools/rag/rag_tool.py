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

It is also where §9.7's trust-tier boundary is enforced (ACCB Mandatory Change 2
/ Review Board Finding C3). Two checks, deliberately in both directions:

- A caller whose profile lacks `may_read_provisional_knowledge` cannot *ask* for
  the low-trust tier — `filters.include_provisional` is rejected here rather
  than quietly downgraded, because a silently-ignored security filter is worse
  than an error: the caller proceeds believing it got what it asked for.
- A caller that did not ask for it cannot *receive* it either, even if the
  backend returns it anyway. That second check is the one that matters. The
  backend is Dify — a system whose filtering we configure but do not implement —
  and a control that trusts the untrusted component to filter itself is not a
  control. `frozenset` allow-lists are checked the same way for the same reason.

Freshness is applied here too, for a related reason: §9.7 requires that stale
market context is never served silently, and the tool is the last point that
sees every chunk before an agent does.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import date

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
from shared.agent_profiles import callers_allowed_for_tool, profile_for
from shared.provenance import ProvenanceLedger
from shared.schemas import (
    AuditSink,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
    TrustTier,
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
    may_read_provisional = profile_for(caller_agent).may_read_provisional_knowledge
    if query.filters.include_provisional and not may_read_provisional:
        # Rejected rather than downgraded to include_provisional=False. Silently
        # narrowing a caller's request would leave it believing it had seen the
        # provisional tier and found nothing there — a false negative on exactly
        # the question §9.7 exists to make answerable.
        raise ToolPermissionError(
            f"'{caller_agent}' is not permitted to retrieve the §9.7 low-trust "
            f'tier (may_read_provisional_knowledge is False for this profile). '
            f'Unapproved knowledge may not inform this agent; see '
            f'shared/agent_profiles/profiles.py.'
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

    result = _apply_trust_and_freshness(result, query, may_read_provisional)

    # §6.1: record what was actually returned, before the caller can act on it.
    # Deliberately after the §9.7 filtering above, not before: the ledger is what
    # an agent's citations are verified against, so recording a chunk this tool
    # then withheld would license a citation to content the agent never legally
    # saw — turning the provenance control into a way around the trust boundary.
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


def _apply_trust_and_freshness(
    result: RetrievalResult,
    query: RetrievalQuery,
    may_read_provisional: bool,
) -> RetrievalResult:
    """§9.7 post-retrieval enforcement, applied to whatever the backend returned.

    Two independent reasons a chunk is dropped here, counted separately because
    they mean different things to the caller: expired market data says "go and
    search again", unverified content says "this exists but nobody has approved
    it yet".

    Note the asymmetry with the request-side check in ``rag_query``. A caller
    *asking* for the low-trust tier without the grant raises — that is the caller
    overreaching, and it should fail loudly at the call site that wrote it. A
    backend *returning* the low-trust tier to a caller that did not ask is a
    different fault: the backend is Dify, its metadata filtering is configuration
    rather than code we own, and the safe response is to withhold the chunks and
    report the count rather than to fail an entire loan assessment on a corpus
    misconfiguration. Either way the content does not reach the agent, which is
    the property §9.7 actually requires.
    """

    if not result.chunks:
        return result

    as_of = query.filters.effective_on or date.today()
    max_age = query.filters.max_market_data_age_days

    kept: list[RetrievedChunk] = []
    expired = 0
    unverified = 0

    for chunk in result.chunks:
        if chunk.is_expired_as_of(as_of, max_age_days=max_age):
            expired += 1
            continue
        if chunk.trust_tier is TrustTier.PROVISIONAL and not may_read_provisional:
            unverified += 1
            continue
        kept.append(chunk)

    if not expired and not unverified:
        return result

    return result.model_copy(
        update={
            'chunks': tuple(kept),
            'withheld_expired': result.withheld_expired + expired,
            'withheld_unverified': result.withheld_unverified + unverified,
            # Left as the backend reported it. `no_confident_match` is §9.5's
            # relevance signal — "candidates existed but scored too low" — and
            # withholding on trust or age is not evidence about relevance. A
            # caller distinguishing an aged-out cache from a weak one reads
            # needs_fresh_search(), which is what that method is for.
            'no_confident_match': result.no_confident_match,
        }
    )


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
