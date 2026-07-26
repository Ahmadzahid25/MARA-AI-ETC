"""Calculation tool — docs/architecture/06-tool-architecture.md §6.2's
calculation row: named formula ID + typed numeric inputs -> numeric result
+ formula version used, restricted to Finance and Risk agents, 2s timeout,
1 retry. Wraps tools/calculations/formulas.py's registry with the same
permission/timeout/retry/audit-log discipline as every other tool
(§6.1) — the formulas themselves are deterministic and real (see that
module's docstring); this module is the Tool Runtime-facing boundary
around them.

``ALLOWED_CALLERS`` is derived from ``shared/agent_profiles`` rather than
hand-maintained, per that registry's own rationale (a grant written down
in two places can drift; ``tests/unit/mara/test_agent_profiles.py`` pins
this as an invariant, the same way ``tools/rag/rag_tool.py`` already does).
"""

from __future__ import annotations

import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError

from pydantic import BaseModel
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
from tools.calculations.formulas import get_formula

TOOL_NAME = 'calculation'
TIMEOUT_SECONDS = 2.0
MAX_ATTEMPTS = 2  # first attempt + 1 retry, per §6.2's "Retries: 1"
ALLOWED_CALLERS = callers_allowed_for_tool(TOOL_NAME)


class CalculationResult(BaseModel):
    formula_id: str
    formula_version: str
    value: float


@retry(
    retry=retry_if_exception_type((ToolTimeoutError, ToolExternalServiceError)),
    stop=stop_after_attempt(MAX_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=5),
    reraise=True,
)
def _run_with_timeout(compute, inputs: dict[str, float]) -> float:
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(compute, inputs)
        try:
            return future.result(timeout=TIMEOUT_SECONDS)
        except FutureTimeoutError as exc:
            raise ToolTimeoutError(
                f'Calculation did not complete within {TIMEOUT_SECONDS}s'
            ) from exc
        except ToolInputError:
            raise
        except Exception as exc:
            raise ToolExternalServiceError(str(exc)) from exc


def calculate(
    formula_id: str,
    inputs: dict[str, float],
    *,
    caller_agent: str,
    workflow_id: str | None = None,
    version: str | None = None,
    audit_sink: AuditSink | None = None,
) -> CalculationResult:
    """Compute ``formula_id`` (optionally pinned to ``version``) over
    ``inputs``. Raises ``ToolPermissionError``, ``ToolInputError``,
    ``ToolTimeoutError``, or ``ToolExternalServiceError`` per §6.1 — never a
    bare ``KeyError``/``ZeroDivisionError`` from the underlying formula.
    """

    if caller_agent not in ALLOWED_CALLERS:
        raise ToolPermissionError(
            f"'{caller_agent}' is not permitted to call the calculation tool "
            f'(allowed: {sorted(ALLOWED_CALLERS)})'
        )

    spec = get_formula(formula_id, version)
    missing = [name for name in spec.required_inputs if name not in inputs]
    if missing:
        raise ToolInputError(
            f'Missing required input(s) for {formula_id!r} {spec.version}: '
            f'{missing}'
        )

    input_hash = hashlib.sha256(
        json.dumps({'formula_id': formula_id, 'version': spec.version, **inputs}, sort_keys=True).encode()
    ).hexdigest()
    started = time.monotonic()

    try:
        value = _run_with_timeout(spec.compute, inputs)
    except ToolInputError:
        _log(
            input_hash, None, started, 'input_error', caller_agent, workflow_id, audit_sink
        )
        raise
    except ToolTimeoutError:
        _log(input_hash, None, started, 'timeout', caller_agent, workflow_id, audit_sink)
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

    result = CalculationResult(
        formula_id=formula_id, formula_version=spec.version, value=value
    )
    output_hash = hashlib.sha256(result.model_dump_json().encode()).hexdigest()
    _log(
        input_hash, output_hash, started, 'success', caller_agent, workflow_id, audit_sink
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
