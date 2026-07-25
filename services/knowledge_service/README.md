# Knowledge service (Dify-backed)

The retrieval boundary agents call — see [`09-knowledge-architecture.md`](../../docs/architecture/09-knowledge-architecture.md) for the full specification this module implements.

§9.1: agents never talk to Dify directly. They call this service, "which is what lets the underlying RAG engine be swapped later without touching agent code" — including the Qdrant scale-out path in [`04-technology-stack.md`](../../docs/architecture/04-technology-stack.md) §4.3.

## What's here

- [`contract.py`](contract.py) — the `KnowledgeBackend` protocol a retrieval engine implements, and `UnconfiguredBackend`, the fail-loud default.
- The types crossing the boundary live in [`shared/schemas/knowledge.py`](../../shared/schemas/knowledge.py), since tools and agents consume them too.

## What's deliberately not here yet

**The Dify adapter.** Standing up Dify — against its own separate database instance, per ACCB Condition C-5 and §9.1.1 — is deployment work, tracked in [`infrastructure/AGENTS.md`](../../infrastructure/AGENTS.md). Defining the contract first is what let the agent-side work (RAG tool, Compliance Agent policy lookup) and the deployment work proceed in parallel rather than one blocking the other.

Implement `KnowledgeBackend.retrieve()` and inject it; nothing above this boundary changes.

## One distinction the adapter must preserve

`KnowledgeBackendNotConfiguredError` is **not** an empty `RetrievalResult`.

An empty result means the corpus was searched and had nothing, which an agent may report as "no applicable policy found" ([`05-agent-architecture.md`](../../docs/architecture/05-agent-architecture.md) §5.4). A missing backend means nothing was searched. Collapsing the two would let a misconfigured deployment produce confident "no applicable policy" findings against a corpus it never reached — an error that looks like a finding.

Likewise, §9.5's "no confident match" is a distinct flag from an empty `chunks`: the backend owns threshold filtering, because reporting `withheld_below_threshold` honestly requires seeing the candidates that were dropped.
