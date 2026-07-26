# Supervisor (deterministic control logic)

Implemented (Milestone 4): `dispatch_task()` — §5.10's retry-vs-escalate
policy wrapped around one task's execution: up to `max_retries` retries
with linear backoff on a systemic-looking failure (`ToolTimeoutError`/
`ToolExternalServiceError` by default, or an injected
`is_systemic_failure` predicate), then `DispatchOutcome.BLOCKED` — returned
as data, never raised, so a workflow node can branch on it and pause for
human intervention (§7.5) rather than crash. A non-systemic failure (bad
input) is never retried.

`CircuitBreaker` — a standard closed → open → half-open → closed cycle,
tripping on consecutive *systemic* failures only (§5.10: "not per-task").
While open, `dispatch_task()` returns `DispatchOutcome.CIRCUIT_OPEN`
without attempting the task at all — distinct from `BLOCKED`, since "we
didn't even try" and "this task exhausted its retries" license different
downstream handling.

LangGraph itself is the actual scheduler in this repo's workflows (the
graph's edges decide what runs next) — this module is the retry/escalate/
circuit-breaker *policy* a workflow node calls into, not a separate
general-purpose dispatch queue. `workflows/loan_assessment` does not yet
call `dispatch_task()` at its own node boundaries (each node calls its
agent directly) — wiring it in is a real follow-up, not done in this slice.

See [05-agent-architecture.md#510-supervisor-reclassified--see-514](../../docs/architecture/05-agent-architecture.md#510-supervisor-reclassified--see-514)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
