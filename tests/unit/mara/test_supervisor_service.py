"""Unit tests for services/supervisor_service/supervisor_service.py."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from services.supervisor_service.supervisor_service import (
    CircuitBreaker,
    CircuitBreakerState,
    DispatchOutcome,
    dispatch_task,
)
from shared.schemas import ToolExternalServiceError, ToolInputError


class TestDispatchTaskSuccess:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_attempt(self) -> None:
        async def task():
            return 'ok'

        result = await dispatch_task('t1', task)

        assert result.outcome == DispatchOutcome.SUCCESS
        assert result.attempts == 1
        assert result.value == 'ok'


class TestRetryPolicy:
    @pytest.mark.asyncio
    async def test_retries_systemic_failure_then_succeeds(self) -> None:
        calls = {'n': 0}

        async def flaky():
            calls['n'] += 1
            if calls['n'] < 3:
                raise ToolExternalServiceError('provider hiccup')
            return 'recovered'

        result = await dispatch_task('t1', flaky, retry_backoff_seconds=0.0)

        assert result.outcome == DispatchOutcome.SUCCESS
        assert result.attempts == 3
        assert result.value == 'recovered'

    @pytest.mark.asyncio
    async def test_blocked_after_exhausting_retries(self) -> None:
        async def always_fails():
            raise ToolExternalServiceError('provider down')

        result = await dispatch_task(
            't1', always_fails, max_retries=2, retry_backoff_seconds=0.0
        )

        assert result.outcome == DispatchOutcome.BLOCKED
        assert result.attempts == 3  # first attempt + 2 retries
        assert 'provider down' in result.error

    @pytest.mark.asyncio
    async def test_non_systemic_failure_is_never_retried(self) -> None:
        calls = {'n': 0}

        async def bad_input():
            calls['n'] += 1
            raise ToolInputError('malformed request')

        result = await dispatch_task(
            't1', bad_input, max_retries=2, retry_backoff_seconds=0.0
        )

        assert result.outcome == DispatchOutcome.BLOCKED
        assert calls['n'] == 1

    @pytest.mark.asyncio
    async def test_custom_is_systemic_failure_predicate(self) -> None:
        calls = {'n': 0}

        class CustomError(Exception):
            pass

        async def flaky():
            calls['n'] += 1
            if calls['n'] < 2:
                raise CustomError('retry me')
            return 'ok'

        result = await dispatch_task(
            't1',
            flaky,
            retry_backoff_seconds=0.0,
            is_systemic_failure=lambda exc: isinstance(exc, CustomError),
        )

        assert result.outcome == DispatchOutcome.SUCCESS
        assert calls['n'] == 2


class TestCircuitBreaker:
    def test_starts_closed(self) -> None:
        breaker = CircuitBreaker()
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.allow_dispatch() is True

    def test_opens_after_consecutive_failures(self) -> None:
        breaker = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            breaker.record_failure(systemic=True)

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.allow_dispatch() is False

    def test_non_systemic_failures_never_open_it(self) -> None:
        breaker = CircuitBreaker(failure_threshold=3)
        for _ in range(10):
            breaker.record_failure(systemic=False)

        assert breaker.state == CircuitBreakerState.CLOSED

    def test_success_resets_consecutive_count(self) -> None:
        breaker = CircuitBreaker(failure_threshold=3)
        breaker.record_failure(systemic=True)
        breaker.record_failure(systemic=True)
        breaker.record_success()
        breaker.record_failure(systemic=True)
        breaker.record_failure(systemic=True)

        assert breaker.state == CircuitBreakerState.CLOSED

    def test_half_opens_after_cooldown(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=60.0)
        breaker.record_failure(systemic=True)
        assert breaker.state == CircuitBreakerState.OPEN

        breaker._opened_at = datetime.now(UTC) - timedelta(seconds=61)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_trial_failure_reopens(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=60.0)
        breaker.record_failure(systemic=True)
        breaker._opened_at = datetime.now(UTC) - timedelta(seconds=61)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        breaker.record_failure(systemic=True)

        # Freshly re-opened — not yet past its own (brand new) cooldown.
        assert breaker.state == CircuitBreakerState.OPEN

    def test_half_open_trial_success_closes(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=60.0)
        breaker.record_failure(systemic=True)
        breaker._opened_at = datetime.now(UTC) - timedelta(seconds=61)
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        breaker.record_success()

        assert breaker.state == CircuitBreakerState.CLOSED


class TestDispatchWithCircuitBreaker:
    @pytest.mark.asyncio
    async def test_open_breaker_prevents_dispatch(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1)
        breaker.record_failure(systemic=True)
        calls = {'n': 0}

        async def task():
            calls['n'] += 1
            return 'ok'

        result = await dispatch_task('t1', task, circuit_breaker=breaker)

        assert result.outcome == DispatchOutcome.CIRCUIT_OPEN
        assert calls['n'] == 0

    @pytest.mark.asyncio
    async def test_dispatch_failure_feeds_the_breaker(self) -> None:
        breaker = CircuitBreaker(failure_threshold=1)

        async def always_fails():
            raise ToolExternalServiceError('down')

        await dispatch_task(
            't1', always_fails, max_retries=0, retry_backoff_seconds=0.0, circuit_breaker=breaker
        )

        assert breaker.state == CircuitBreakerState.OPEN


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_success_is_logged(self) -> None:
        entries = []

        async def task():
            return 'ok'

        await dispatch_task('t1', task, audit_sink=entries.append)

        assert len(entries) == 1
        assert entries[0].metadata['dispatch_outcome'] == 'success'

    @pytest.mark.asyncio
    async def test_blocked_is_logged(self) -> None:
        entries = []

        async def always_fails():
            raise ToolExternalServiceError('down')

        await dispatch_task(
            't1', always_fails, max_retries=0, retry_backoff_seconds=0.0, audit_sink=entries.append
        )

        assert len(entries) == 1
        assert entries[0].metadata['dispatch_outcome'] == 'blocked'
