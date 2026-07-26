# Market Agent

Implemented (Milestone 3): `MarketAgent.gather_market_context()` — the only
agent with a real outbound-search code path (`tools/search`), combined with
a RAG query against previously cached market findings via the real
Milestone-2 Knowledge Service boundary
(`services.knowledge_service.contract.KnowledgeBackend`,
`tools.rag.rag_tool.rag_query`, scoped to `DocumentKind.MARKET_DATA`).
Source-credibility scoring (0.7 threshold, §5.7) is the one genuinely
agentic step — Sonnet-tier LLM call, injectable `credibility_assessor` for
tests; low-credibility claims are labeled (`MarketClaim.is_low_credibility`),
never silently dropped.

Real failure handling: a search-tool timeout/external-service error
degrades to Knowledge Base-only results with an explicit
`MarketBrief.note`, and an empty claim set is reported as "insufficient
external data" — neither is a stub, both are exercised in
`tests/unit/mara/test_market_agent.py`.

**Not implemented / genuinely open:**
- §9.7's low-trust-tier provisional visibility (a cached market finding
  readable before Knowledge Owner approval) has no equivalent yet in
  `shared/schemas/knowledge.py`'s `RetrievalFilters` — this agent currently
  only ever reads already-approved market data, same as any other query.
- Writing a freshly-gathered brief back into Knowledge Memory has no
  binding either: `KnowledgeBackend` is read-only (one method,
  `retrieve()`), so `CacheWriter` stays an injectable seam with nothing to
  bind it to until an ingestion path exists. (The Milestone-3 slice that
  preceded this reconciliation had a `knowledge_cache.py` binder against a
  since-superseded, non-Protocol Knowledge Service design — dropped along
  with that design, not carried forward as dead code.)
- An unconfigured `KnowledgeBackend` (`backend=None`) degrades the cached-
  data lookup to "nothing cached yet" (`KnowledgeBackendNotConfiguredError`
  is caught, not propagated) rather than failing the whole call — unlike
  `agents/compliance_agent`'s policy lookup, cached market data is
  supplementary to this agent's primary source (live search), so an
  unconfigured backend here doesn't risk the "confidently searched and
  found nothing" dishonesty a missing policy corpus would.
- The real search provider (`tools/search`'s `engine`), the
  query-sanitizer's free-text name-detection gap
  (`tools/search/query_sanitizer.py`'s `name_detector`), and the
  Kubernetes network-policy egress control (§6.6's other,
  infrastructure-only mandatory control) — see `infrastructure/AGENTS.md`.

See [05-agent-architecture.md#57-market-agent](../../docs/architecture/05-agent-architecture.md#57-market-agent)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
