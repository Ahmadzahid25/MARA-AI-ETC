"""The Knowledge Service boundary — docs/architecture/09-knowledge-architecture.md §9.1.

Dify sits behind this interface, and nothing above it knows that. §9.1 makes the
reason explicit: agents call the service, not Dify, "which is what lets the
underlying RAG engine be swapped later without touching agent code." A swap is
only cheap if the seam is a typed protocol rather than Dify's own response shape
travelling upward, so this module defines the seam and
`shared/schemas/knowledge.py` defines what crosses it.

What is deliberately *not* here: the Dify adapter itself. Standing up Dify —
against its own separate database instance, per ACCB Condition C-5 and §9.1.1 —
is deployment work owned by the infrastructure/backend team, and it is tracked
in infrastructure/AGENTS.md. Defining the contract first is what lets that work
and the agent-side work (the RAG tool, the Compliance Agent's policy lookup)
proceed in parallel instead of one blocking the other.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from shared.schemas.knowledge import RetrievalQuery, RetrievalResult


@runtime_checkable
class KnowledgeBackend(Protocol):
    """What a retrieval engine must provide to back this service.

    A Protocol rather than a base class so the Dify adapter, an in-memory test
    double, and a future Qdrant-backed implementation
    (docs/architecture/04-technology-stack.md §4.3's scale-out path) are
    interchangeable without a shared inheritance root.
    """

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """Return chunks matching ``query``, already filtered by the metadata in
        ``query.filters`` and by ``query.min_relevance``.

        Implementations own threshold filtering rather than returning everything
        for the caller to trim, because §9.5's "no confident match" is a
        retrieval-side determination: it needs the candidates that were dropped
        in order to report ``withheld_below_threshold`` honestly.
        """
        ...


class KnowledgeBackendNotConfiguredError(RuntimeError):
    """No retrieval backend is wired up in this environment.

    Raised rather than returning an empty result on purpose. An empty
    `RetrievalResult` means "the corpus was searched and had nothing", which an
    agent is entitled to report as "no applicable policy found"
    (docs/architecture/05-agent-architecture.md §5.4). A missing backend means
    nothing was searched at all, and silently collapsing the two would let a
    misconfigured deployment produce confident "no applicable policy" findings
    against a corpus it never reached.
    """


class UnconfiguredBackend:
    """Default backend: fails loudly.

    Present so that `services/knowledge_service` is importable and the RAG tool
    is testable before Dify exists, without any code path that quietly behaves
    as though an empty corpus were a real answer.
    """

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        raise KnowledgeBackendNotConfiguredError(
            'No KnowledgeBackend is configured. Wire the Dify-backed adapter '
            '(see infrastructure/AGENTS.md) or inject a test double; retrieval '
            'must not be attempted against an unconfigured corpus.'
        )
