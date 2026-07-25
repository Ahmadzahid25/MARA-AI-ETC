# shared/provenance

Deterministic citation verification — [`06-tool-architecture.md`](../../docs/architecture/06-tool-architecture.md) §6.1, closing Review Board Finding A2.

## The property

**An agent cannot make a citation valid by asserting it — only by having caused a tool to return it.**

Tools write the ledger (`record_returned`). Agents never do. Verification reads it before an agent's output leaves the task. That asymmetry is the entire design.

## Why schema validation isn't enough

A fabricated citation is well-formed by construction: the LLM produces a plausible document ID and clause number, the Pydantic model accepts it, and it reaches an officer looking *more* trustworthy than an omitted citation would. §6.1 requires the check be deterministic and sit outside the agent for exactly that reason.

## Usage

```python
ledger = ProvenanceLedger()  # one per agent task

result = await rag_query(query, caller_agent=..., ledger=ledger)  # tool records

ledger.require_verified(tuple(c.to_citable_ref() for c in citations))  # before output
```

Use `verify()` instead of `require_verified()` when partial results should reach the officer with rejections rendered rather than the whole output blocked.

## Two behaviors worth knowing before you rely on it

- **Fails closed.** An empty ledger rejects every citation. "No tool ran" and "the agent may cite freely" must never be the same state, and the likeliest route to an empty ledger is a caller that forgot to pass one.
- **Version participates in identity.** Citing v4 when the tool returned v3 is a rejection, not a match — [`09-knowledge-architecture.md`](../../docs/architecture/09-knowledge-architecture.md) §9.4 requires an audit of a March decision to see March's policy text.

## Not yet unified

`agents/document_agent/` runs its own equivalent check inline (`_source_for_page` rejects a field citing a page that was never parsed). It predates this module and is correct as-is; folding it into the ledger is worthwhile but deliberately not done here, since the fabrication risk this module targets is concentrated in retrieval, where the agent sees identifiers it could plausibly invent.
