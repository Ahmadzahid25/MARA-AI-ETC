# tools/rag

RAG / knowledge query tool — [`06-tool-architecture.md`](../../docs/architecture/06-tool-architecture.md) §6.2.

| | |
|---|---|
| Permissions | All 7 agents — derived from [`shared/agent_profiles/`](../../shared/agent_profiles/) per §6.7, never restated here |
| Timeout | 10s |
| Retries | 2, exponential backoff, on timeout/external-service failure |

Calls [`services/knowledge_service`](../../services/knowledge_service/), never Dify directly.

## Why this tool carries the provenance ledger

It is the first tool whose output an agent cites at scale, which makes it the first place §6.1's citation-verification control actually bites. Every chunk returned is recorded into the task's `ProvenanceLedger` before the caller can act on it, so an agent citing a clause that was never retrieved is caught deterministically.

Recording happens inside the tool for the same reason invocation logging does: the record must exist even if the agent's subsequent reasoning crashes.

**Pass a `ledger` if the caller intends to cite.** Omitting it is not an error, but verification then runs against an empty ledger and fails closed — every citation rejected. That is the right direction to fail; it just means the omission surfaces later than it should.
