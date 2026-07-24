"""Common tool contract types — docs/architecture/06-tool-architecture.md
§6.1: every tool reasons over a typed error taxonomy rather than raw
exceptions leaking to the caller, and every tool invocation is logged
(agent ID, workflow ID, input hash, output hash, latency, outcome) before
its result is returned to the caller — "so a tool call is audit-recorded
even if the agent's own subsequent reasoning crashes."

The real write path is services/audit_service (not yet built — Milestone 1,
later slice than this one). ToolInvocationLog and log_tool_invocation() here
are the stable *shape* tools log against now; a later task points the sink
at the real Audit Memory table without changing any tool's call site.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger('mara.tool_audit')


class ToolError(Exception):
    """Base of the typed error taxonomy every tool must raise instead of a
    bare/library-native exception, per §6.1. Agents reason over these typed
    errors, not stack traces.
    """


class ToolInputError(ToolError):
    """Malformed or invalid input — rejected before the tool implementation
    does any real work."""


class ToolTimeoutError(ToolError):
    """The tool's per-call timeout (declared in the §6.2 catalogue, e.g. 30s
    for OCR) was exceeded. Idempotent tools get automatic retry with
    backoff on this error per §6.1 — see tools/ocr and tools/documents."""


class ToolExternalServiceError(ToolError):
    """A dependency the tool calls out to (an OCR engine process, an
    external API) failed or errored. Also eligible for automatic retry on
    idempotent tools, per §6.1."""


class ToolPermissionError(ToolError):
    """The calling agent is not on the tool's permission allow-list (§6.2's
    Permissions column) — enforced here, at the tool boundary, not merely
    documented or left to the calling agent's own discipline."""


ToolOutcome = Literal['success', 'input_error', 'timeout', 'external_error', 'denied']


class ToolInvocationLog(BaseModel):
    """One tool-call record, per §6.1's required fields. ``input_hash`` /
    ``output_hash`` are hashes, not the raw payloads — the audit record
    proves a call happened with specific input/output without duplicating
    potentially sensitive document content into the audit trail itself.
    """

    tool_name: str
    caller_agent: str
    workflow_id: str | None = Field(
        default=None,
        description='None for tool calls made outside a workflow instance '
        '(e.g. ad hoc testing) — real invocations should always carry one.',
    )
    input_hash: str
    output_hash: str | None = Field(
        default=None, description='None when the call did not succeed.'
    )
    latency_ms: float = Field(ge=0.0)
    outcome: ToolOutcome
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


AuditSink = Callable[[ToolInvocationLog], None]


def _default_sink(entry: ToolInvocationLog) -> None:
    # TODO(milestone-1): replace with a real services/audit_service write
    # once that service exists. Structured logging is a deliberate, visible
    # stand-in — not a silent no-op — so a missing real audit write is
    # obvious in logs during this interim period, not swallowed quietly.
    logger.info('tool_invocation', extra={'audit': entry.model_dump(mode='json')})


def log_tool_invocation(
    entry: ToolInvocationLog, sink: AuditSink | None = None
) -> None:
    """Record one tool invocation. Tools call this themselves, always,
    before returning a result or raising — see tools/ocr and
    tools/documents for the call sites. ``sink`` is injectable so callers
    (and tests) can capture entries without depending on the interim
    logging fallback.
    """

    (sink or _default_sink)(entry)
