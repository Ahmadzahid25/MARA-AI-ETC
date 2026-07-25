"""RAG-backed policy lookup for the Compliance Agent — Milestone 2.

Replaces the Milestone-1 stub that returned no citations for every requirement.
The agent's own structure is unchanged, which was the point of stubbing at the
`policy_lookup` seam rather than inside the agent
(agents/compliance_agent/compliance_agent.py's module docstring): Milestone 2
swaps the lookup, not the checklist logic or the escalation rules.

Two behaviors here are specified, not incidental:

- **Retrieval is scoped to currently-effective policy** (§9.3). Similarity
  search alone will surface a superseded clause that reads almost identically to
  the current one, and the resulting citation is well-formed and wrong in a way
  no officer could spot from the output.
- **"No confident match" is not "no applicable policy"** (§9.5, §5.4). A
  retrieval whose candidates all fell below the relevance threshold returns no
  citations, which the agent reports as NO_POLICY_FOUND — the honest answer.
  What must never happen is a weak match being passed through as support, so the
  threshold is applied at retrieval and the agent never sees the discards.
"""

from __future__ import annotations

from agents.compliance_agent.compliance_agent import PolicyLookup
from services.knowledge_service.contract import KnowledgeBackend
from shared.llm.model_tiers import AgentName
from shared.provenance import ProvenanceLedger
from shared.schemas import AuditSink
from shared.schemas.knowledge import (
    DocumentKind,
    PolicyCitation,
    RetrievalFilters,
    RetrievalQuery,
)
from tools.rag.rag_tool import rag_query

DEFAULT_TOP_K = 5
DEFAULT_MIN_RELEVANCE = 0.6


def make_rag_policy_lookup(
    backend: KnowledgeBackend,
    *,
    ledger: ProvenanceLedger,
    workflow_id: str | None = None,
    top_k: int = DEFAULT_TOP_K,
    min_relevance: float = DEFAULT_MIN_RELEVANCE,
    audit_sink: AuditSink | None = None,
) -> PolicyLookup:
    """Build a ``PolicyLookup`` that queries the knowledge corpus.

    ``ledger`` is required rather than optional, unlike on the tool itself: a
    compliance finding always cites, so a lookup that did not record what it
    retrieved would produce citations that fail verification later, further from
    the cause. Requiring it here puts the error at construction time instead.
    """

    async def lookup(requirement: str) -> list[PolicyCitation]:
        result = await rag_query(
            RetrievalQuery(
                query=requirement,
                top_k=top_k,
                min_relevance=min_relevance,
                filters=RetrievalFilters(
                    document_kinds=frozenset({DocumentKind.POLICY}),
                    # effective_on=None means "in force at query time"; see
                    # RetrievalFilters — never "any version".
                    include_superseded=False,
                ),
            ),
            caller_agent=AgentName.COMPLIANCE.value,
            workflow_id=workflow_id,
            backend=backend,
            ledger=ledger,
            audit_sink=audit_sink,
        )
        if result.no_confident_match:
            return []
        return [PolicyCitation.from_chunk(chunk) for chunk in result.chunks]

    return lookup
