"""RAG tool tests — docs/architecture/06-tool-architecture.md §6.2 and
docs/architecture/09-knowledge-architecture.md §9.5.
"""

from __future__ import annotations

import asyncio

import pytest

from services.knowledge_service import KnowledgeBackendNotConfiguredError
from shared.provenance import CitableRef, ProvenanceLedger
from shared.schemas import (
    ToolExternalServiceError,
    ToolInputError,
    ToolInvocationLog,
    ToolPermissionError,
    ToolTimeoutError,
)
from shared.schemas.knowledge import (
    DocumentKind,
    RetrievalQuery,
    RetrievalResult,
    RetrievedChunk,
    SensitivityClass,
)
from tools.rag.rag_tool import ALLOWED_CALLERS, TOOL_NAME, rag_query

CHUNK = RetrievedChunk(
    document_id='policy-1',
    version='v3',
    locator='4.2',
    text='Applicants must hold a valid business registration.',
    relevance=0.91,
    document_kind=DocumentKind.POLICY,
    sensitivity=SensitivityClass.INTERNAL,
)


class StubBackend:
    def __init__(self, result: RetrievalResult) -> None:
        self.result = result
        self.calls: list[RetrievalQuery] = []

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        self.calls.append(query)
        return self.result


class FailingBackend:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.attempts = 0

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        self.attempts += 1
        raise self.exc


def _query(text: str = 'business registration requirement') -> RetrievalQuery:
    return RetrievalQuery(query=text)


# ── Permissions (§6.2, derived per §6.7) ──


def test_allow_list_covers_every_agent_that_needs_knowledge() -> None:
    assert 'compliance_agent' in ALLOWED_CALLERS
    assert 'recommendation_agent' in ALLOWED_CALLERS


def test_an_ungranted_caller_is_rejected() -> None:
    with pytest.raises(ToolPermissionError, match='not permitted'):
        asyncio.run(rag_query(_query(), caller_agent='notification_service'))


# ── Input validation ──


def test_blank_query_is_rejected_before_the_backend_is_touched() -> None:
    backend = StubBackend(RetrievalResult())
    with pytest.raises(ToolInputError):
        asyncio.run(
            rag_query(
                RetrievalQuery(query='   '),
                caller_agent='compliance_agent',
                backend=backend,
            )
        )
    assert backend.calls == []


# ── Provenance recording (§6.1) ──


def test_returned_chunks_are_recorded_in_the_ledger() -> None:
    ledger = ProvenanceLedger()
    backend = StubBackend(RetrievalResult(chunks=(CHUNK,)))

    asyncio.run(
        rag_query(
            _query(),
            caller_agent='compliance_agent',
            backend=backend,
            ledger=ledger,
        )
    )

    assert ledger.returned_by(TOOL_NAME) == frozenset(
        {CitableRef(document_id='policy-1', version='v3', locator='4.2')}
    )


def test_a_citation_the_tool_did_not_return_still_fails_verification() -> None:
    """The end-to-end shape of Finding A2: retrieving one clause does not
    license citing a neighbouring one."""

    ledger = ProvenanceLedger()
    asyncio.run(
        rag_query(
            _query(),
            caller_agent='compliance_agent',
            backend=StubBackend(RetrievalResult(chunks=(CHUNK,))),
            ledger=ledger,
        )
    )

    fabricated = CitableRef(document_id='policy-1', version='v3', locator='9.9')
    assert ledger.verify((fabricated,)).rejected == (fabricated,)


# ── §9.5 "no confident match" ──


def test_no_confident_match_is_distinguishable_from_an_empty_corpus() -> None:
    weak = RetrievalResult(no_confident_match=True, withheld_below_threshold=4)
    empty = RetrievalResult()

    assert weak.chunks == empty.chunks == ()
    assert weak.no_confident_match and not empty.no_confident_match
    assert weak.withheld_below_threshold == 4


# ── Failure handling (§6.1) ──


def test_unconfigured_backend_raises_rather_than_returning_empty() -> None:
    """A missing corpus must not be indistinguishable from an empty one — an
    agent is entitled to report "no applicable policy found" for the second and
    must not for the first."""

    with pytest.raises(KnowledgeBackendNotConfiguredError):
        asyncio.run(rag_query(_query(), caller_agent='compliance_agent'))


def test_unconfigured_backend_is_not_retried() -> None:
    backend = FailingBackend(KnowledgeBackendNotConfiguredError('nope'))

    with pytest.raises(KnowledgeBackendNotConfiguredError):
        asyncio.run(
            rag_query(_query(), caller_agent='compliance_agent', backend=backend)
        )

    assert backend.attempts == 1, 'a deployment fault should not be retried'


def test_backend_errors_surface_as_typed_tool_errors_after_retrying() -> None:
    backend = FailingBackend(RuntimeError('dify exploded'))

    with pytest.raises(ToolExternalServiceError):
        asyncio.run(
            rag_query(_query(), caller_agent='compliance_agent', backend=backend)
        )

    assert backend.attempts == 3, 'first attempt + 2 retries, per §6.2'


def test_a_slow_backend_times_out_as_a_typed_error() -> None:
    class SlowBackend:
        async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
            await asyncio.sleep(30)
            raise AssertionError('should have timed out')

    import tools.rag.rag_tool as rag_module

    original = rag_module.TIMEOUT_SECONDS
    rag_module.TIMEOUT_SECONDS = 0.01
    try:
        with pytest.raises(ToolTimeoutError):
            asyncio.run(
                rag_query(
                    _query(), caller_agent='compliance_agent', backend=SlowBackend()
                )
            )
    finally:
        rag_module.TIMEOUT_SECONDS = original


# ── Audit logging (§6.1) ──


def test_every_invocation_is_audit_logged_with_the_tool_name() -> None:
    entries: list[ToolInvocationLog] = []
    asyncio.run(
        rag_query(
            _query(),
            caller_agent='compliance_agent',
            workflow_id='wf-1',
            backend=StubBackend(RetrievalResult(chunks=(CHUNK,))),
            audit_sink=entries.append,
        )
    )

    assert len(entries) == 1
    assert entries[0].tool_name == TOOL_NAME
    assert entries[0].caller_agent == 'compliance_agent'
    assert entries[0].workflow_id == 'wf-1'
    assert entries[0].outcome == 'success'


def test_a_failed_call_is_audit_logged_too() -> None:
    entries: list[ToolInvocationLog] = []

    with pytest.raises(ToolExternalServiceError):
        asyncio.run(
            rag_query(
                _query(),
                caller_agent='compliance_agent',
                backend=FailingBackend(RuntimeError('boom')),
                audit_sink=entries.append,
            )
        )

    assert [e.outcome for e in entries] == ['external_error']
