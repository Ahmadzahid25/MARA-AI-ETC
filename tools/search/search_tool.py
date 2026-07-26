"""Web/external search tool — docs/architecture/06-tool-architecture.md
§6.2's row:

    Input: Sanitized query (PII stripped/generalized before this tool is
    even called — see §6.6), domain allow-list ref
    Output: Ranked results with URL/snippet/retrieved-date
    Permissions: Market Agent only
    Timeout: 15s
    Retries: 2
    Notes: "The only tool with outbound internet access; network-policy-
    enforced at the infrastructure level to the Market Agent's pod
    specifically; every call logged with full (sanitized) query text"

**Milestone 3 slice.** Sanitization (§6.6, tools/search/query_sanitizer.py)
runs *inside* this tool, not merely before it — "the web/external search
tool itself ... enforces" sanitization per §6.6, so a caller cannot bypass
it by sanitizing loosely and calling in anyway. Domain allow-list filtering
is real, deterministic post-processing of whatever the search engine
returns. **No real search provider is wired** — the actual engine (which
vendor, which API) is an undecided choice, same category as `tools/ocr`'s
OCR engine; ``engine`` is injectable with an honest "not wired" default.
Network-policy-level egress enforcement (§6.6's second control) is
infrastructure, not application code — see infrastructure/AGENTS.md's
request list; this module cannot itself guarantee that layer.

``ALLOWED_CALLERS`` is derived from ``shared/agent_profiles`` rather than
hand-maintained — see ``tools/calculations/calculation_tool.py``'s
docstring for the same reasoning and the invariant test that enforces it.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import UTC, datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from shared.agent_profiles import callers_allowed_for_tool
from shared.schemas import (
    AuditSink,
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
    log_tool_invocation,
)
from tools.search.query_sanitizer import NameDetector, sanitize_query

TOOL_NAME = 'web_search'
TIMEOUT_SECONDS = 15.0
MAX_ATTEMPTS = 3  # first attempt + 2 retries, per §6.2's "Retries: 2"
ALLOWED_CALLERS = callers_allowed_for_tool(TOOL_NAME)


class SearchResult(BaseModel):
    url: str
    title: str
    snippet: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Runs one sanitized query against the real provider, returning raw
# (unfiltered) results. No default — see module docstring.
SearchEngine = Callable[[str], list[SearchResult]]


def _default_engine(sanitized_query: str) -> list[SearchResult]:
    raise ToolExternalServiceError(
        'No search engine is wired in this environment. Inject an `engine` '
        'callable — the real provider choice is not decided yet.'
    )


def _domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix('www.')


@retry(
    retry=retry_if_exception_type((ToolTimeoutError, ToolExternalServiceError)),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _run_engine_with_timeout(
    engine: SearchEngine, sanitized_query: str
) -> list[SearchResult]:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(engine, sanitized_query)
        try:
            return future.result(timeout=TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            raise ToolTimeoutError(
                f'Search did not complete within {TIMEOUT_SECONDS}s'
            ) from exc
        except (ToolTimeoutError, ToolExternalServiceError):
            raise
        except Exception as exc:
            raise ToolExternalServiceError(str(exc)) from exc


def run_search(
    query: str,
    *,
    caller_agent: str,
    allowed_domains: frozenset[str],
    workflow_id: str | None = None,
    engine: SearchEngine | None = None,
    name_detector: NameDetector | None = None,
    audit_sink: AuditSink | None = None,
) -> list[SearchResult]:
    """Sanitize ``query`` (§6.6, always — this is the enforcement point,
    not the Market Agent's prompt discipline), run it against ``engine``,
    and filter results to ``allowed_domains``. Raises
    ``ToolPermissionError``, ``ToolInputError``, ``ToolTimeoutError``, or
    ``ToolExternalServiceError`` per §6.1 — including when sanitization
    itself rejects the query as ungeneralizable.
    """

    if caller_agent not in ALLOWED_CALLERS:
        raise ToolPermissionError(
            f"'{caller_agent}' is not permitted to call the web/external "
            f'search tool (allowed: {sorted(ALLOWED_CALLERS)})'
        )
    if not allowed_domains:
        raise ToolInputError('allowed_domains must not be empty')

    # Sanitization failures are input errors, not logged as an executed
    # (even if failed) outbound call — no outbound request was ever
    # constructed for this query.
    sanitized_query = sanitize_query(query, name_detector=name_detector)

    input_hash = hashlib.sha256(sanitized_query.encode()).hexdigest()
    started = time.monotonic()
    active_engine = engine or _default_engine

    try:
        raw_results = _run_engine_with_timeout(active_engine, sanitized_query)
    except ToolTimeoutError:
        _log(
            input_hash,
            None,
            started,
            'timeout',
            caller_agent,
            workflow_id,
            sanitized_query,
            frozenset(),
            audit_sink,
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
            sanitized_query,
            frozenset(),
            audit_sink,
        )
        raise

    results = [r for r in raw_results if _domain_of(r.url) in allowed_domains]
    domains_hit = frozenset(_domain_of(r.url) for r in results)

    output_hash = hashlib.sha256(
        '|'.join(r.model_dump_json() for r in results).encode()
    ).hexdigest()
    _log(
        input_hash,
        output_hash,
        started,
        'success',
        caller_agent,
        workflow_id,
        sanitized_query,
        domains_hit,
        audit_sink,
    )
    return results


def _log(
    input_hash: str,
    output_hash: str | None,
    started_at: float,
    outcome: str,
    caller_agent: str,
    workflow_id: str | None,
    sanitized_query: str,
    domains_hit: frozenset[str],
    audit_sink: AuditSink | None,
) -> None:
    # §6.2: "every call logged with full (sanitized) query text" and §5.7:
    # "every call logged with query and domains hit" — both go in
    # ToolInvocationLog.metadata, the one tool-specific field no other tool
    # in this repo currently needs.
    log_tool_invocation(
        ToolInvocationLog(
            tool_name=TOOL_NAME,
            caller_agent=caller_agent,
            workflow_id=workflow_id,
            input_hash=input_hash,
            output_hash=output_hash,
            latency_ms=(time.monotonic() - started_at) * 1000,
            outcome=outcome,  # type: ignore[arg-type]
            metadata={
                'sanitized_query': sanitized_query,
                'domains_hit': sorted(domains_hit),
            },
        ),
        sink=audit_sink,
    )
