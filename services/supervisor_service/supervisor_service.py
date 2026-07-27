"""Supervisor — docs/architecture/05-agent-architecture.md §5.10.

    "Supervisor is not an agent as of v1.0. It is deterministic control
    logic — dispatch, per-agent budget/permission enforcement, retry-vs-
    escalate-vs-fail policy evaluation — implemented as LangGraph control
    flow, with no LLM prompt, confidence threshold, or escalation-target
    concept of its own... every decision it takes (retry this task,
    escalate that one, mark a workflow blocked) is policy evaluation over
    already-known state, not reasoning over uncertain input."

**Milestone 4 slice.** ``dispatch_task()`` is the concrete shape this takes
in a LangGraph-based workflow: LangGraph itself is the actual scheduler
(the graph's own edges decide *what* runs next), so Supervisor's job here
is the retry/escalate/circuit-breaker *policy* wrapped around one node's
execution — called from inside a workflow node
(``workflows/loan_assessment``), not a separate general-purpose queue.

Per §5.10's failure handling: on retry exhaustion, the task is marked
failed and returned as data (``DispatchOutcome.BLOCKED``), never raised —
a workflow node branches on this to pause for human intervention (§7.5),
which is a decision the *workflow*, not this module, makes. A circuit
breaker trips on systemic (cross-task) failure, pausing new dispatch
platform-wide rather than letting every in-flight task retry
independently against a provider that is already down.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TypeVar

from pydantic import BaseModel, Field

from shared.schemas import AuditSink, ToolExternalServiceError, ToolTimeoutError
from shared.schemas.tooling import ToolInvocationLog, log_tool_invocation

T = TypeVar('T')

DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_SECONDS = 1.0


class DispatchOutcome(str, Enum):
    SUCCESS = 'success'
    BLOCKED = 'blocked'
    CIRCUIT_OPEN = 'circuit_open'


class DispatchResult(BaseModel):
    """§5.10: "Outputs: Dispatch commands, retry decisions, escalation
    events, workflow status updates." One dispatch attempt's outcome, as
    data a workflow node branches on rather than an exception it must
    catch."""

    model_config = {'arbitrary_types_allowed': True}

    task_name: str
    outcome: DispatchOutcome
    attempts: int = Field(ge=0)
    value: object = None
    error: str | None = None


# A failure this predicate returns True for counts toward the circuit
# breaker (cross-task, provider-level degradation); False means it's this
# task's own problem (bad input, permission) and must not trip the breaker
# for every other, unrelated task.
IsSystemicFailure = Callable[[Exception], bool]


def _default_is_systemic(exc: Exception) -> bool:
    return isinstance(exc, (ToolTimeoutError, ToolExternalServiceError))


class CircuitBreakerState(str, Enum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


class CircuitBreaker:
    """§5.10: "a circuit breaker trips on systemic (not per-task) LLM/
    provider degradation, pausing new dispatch platform-wide rather than
    letting every in-flight workflow retry independently."

    Standard closed → open → half-open → closed cycle: ``failure_threshold``
    consecutive systemic failures opens it; after ``cooldown_seconds`` one
    trial dispatch is allowed through (half-open); that trial's outcome
    decides whether it closes again or re-opens.
    """

    def __init__(
        self, *, failure_threshold: int = 5, cooldown_seconds: float = 30.0
    ) -> None:
        self._failure_threshold = failure_threshold
        self._cooldown_seconds = cooldown_seconds
        self._state = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._opened_at: datetime | None = None

    @property
    def state(self) -> CircuitBreakerState:
        if (
            self._state == CircuitBreakerState.OPEN
            and self._opened_at is not None
            and datetime.now(UTC) - self._opened_at
            >= timedelta(seconds=self._cooldown_seconds)
        ):
            self._state = CircuitBreakerState.HALF_OPEN
        return self._state

    def allow_dispatch(self) -> bool:
        return self.state != CircuitBreakerState.OPEN

    def record_success(self) -> None:
        self._consecutive_failures = 0
        self._state = CircuitBreakerState.CLOSED
        self._opened_at = None

    def record_failure(self, *, systemic: bool) -> None:
        if not systemic:
            return
        if self.state == CircuitBreakerState.HALF_OPEN:
            # The trial dispatch failed too — back to fully open, fresh cooldown.
            self._state = CircuitBreakerState.OPEN
            self._opened_at = datetime.now(UTC)
            return
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._failure_threshold:
            self._state = CircuitBreakerState.OPEN
            self._opened_at = datetime.now(UTC)


async def dispatch_task(
    task_name: str,
    task_fn: Callable[[], Awaitable[T]],
    *,
    workflow_id: str | None = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_backoff_seconds: float = DEFAULT_RETRY_BACKOFF_SECONDS,
    circuit_breaker: CircuitBreaker | None = None,
    is_systemic_failure: IsSystemicFailure = _default_is_systemic,
    audit_sink: AuditSink | None = None,
) -> DispatchResult:
    """Run ``task_fn`` with §5.10's retry-vs-escalate policy: up to
    ``max_retries`` retries with linear backoff on a systemic-looking
    failure, then ``BLOCKED`` rather than raising. A non-systemic failure
    (e.g. bad input) is never retried — retrying a task that is wrong
    regardless of provider health just delays the same failure.

    If ``circuit_breaker`` is supplied and open, the task is not attempted
    at all — ``CIRCUIT_OPEN``, distinct from ``BLOCKED``, since "we didn't
    even try because the provider is known-down" is a different fact than
    "this specific task exhausted its retries."
    """

    if circuit_breaker is not None and not circuit_breaker.allow_dispatch():
        _log(task_name, workflow_id, 'circuit_open', 0, audit_sink)
        return DispatchResult(
            task_name=task_name, outcome=DispatchOutcome.CIRCUIT_OPEN, attempts=0
        )

    last_error: Exception | None = None
    for attempt in range(1, max_retries + 2):  # first attempt + max_retries
        try:
            value = await task_fn()
        except Exception as exc:  # noqa: BLE001 - policy evaluates any failure
            last_error = exc
            systemic = is_systemic_failure(exc)
            if circuit_breaker is not None:
                circuit_breaker.record_failure(systemic=systemic)
            if not systemic or attempt > max_retries:
                break
            await asyncio.sleep(retry_backoff_seconds * attempt)
            continue
        else:
            if circuit_breaker is not None:
                circuit_breaker.record_success()
            _log(task_name, workflow_id, 'success', attempt, audit_sink)
            return DispatchResult(
                task_name=task_name,
                outcome=DispatchOutcome.SUCCESS,
                attempts=attempt,
                value=value,
            )

    _log(
        task_name, workflow_id, 'blocked', max_retries + 1, audit_sink, error=last_error
    )
    return DispatchResult(
        task_name=task_name,
        outcome=DispatchOutcome.BLOCKED,
        attempts=max_retries + 1,
        error=str(last_error) if last_error else None,
    )


def _log(
    task_name: str,
    workflow_id: str | None,
    outcome: str,
    attempts: int,
    audit_sink: AuditSink | None,
    *,
    error: Exception | None = None,
) -> None:
    log_tool_invocation(
        ToolInvocationLog(
            tool_name='supervisor_dispatch',
            caller_agent='supervisor_service',
            workflow_id=workflow_id,
            input_hash=task_name,
            output_hash=str(error) if error else None,
            latency_ms=0.0,
            outcome='success' if outcome == 'success' else 'external_error',
            metadata={
                'task_name': task_name,
                'dispatch_outcome': outcome,
                'attempts': attempts,
            },
        ),
        sink=audit_sink,
    )
