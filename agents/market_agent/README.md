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

**§9.7's low-trust tier — implemented (read side):**
- `TrustTier` is a required field on every `RetrievedChunk` and
  `PolicyCitation`, so no construction site can omit it and no backend can
  launder unreviewed content in by forgetting to map it.
- `RetrievalFilters.include_provisional` opts in, and asking is itself
  permission-checked: `may_read_provisional_knowledge` is set on this
  agent's profile and no other. `tools/rag/rag_tool.py` enforces it in both
  directions — an ungranted caller cannot ask, and cannot receive it even if
  the backend returns it anyway. That second check is the one that matters,
  since Dify's metadata filtering is configuration we send rather than code
  we own.
- Withheld chunks are not recorded in the `ProvenanceLedger`, so a citation
  to unapproved content fails §6.1 verification instead of passing on the
  strength of having been retrieved. The two controls compose rather than
  cancelling out.
- Freshness: cached market data past `MARKET_DATA_FRESHNESS_DAYS` (90,
  overridable per sector via `max_market_data_age_days`) is withheld, and
  `RetrievalResult.needs_fresh_search()` distinguishes "the cache aged out,
  go and search" from §9.5's "candidates scored too low". A `MARKET_DATA`
  chunk with no `cached_at` counts as expired — an age that cannot be
  established is not evidence of freshness.

**Not implemented / genuinely open:**
- Writing a freshly-gathered brief back into Knowledge Memory.
  `KnowledgeBackend` is read-only (one method, `retrieve()`), so
  `CacheWriter` stays an injectable seam with nothing to bind it to until an
  ingestion path exists — which means nothing writes
  `TrustTier.PROVISIONAL` content today. The read-side boundary is
  deliberately built and enforced ahead of the writer that will populate it,
  so the control is in place before there is anything for it to contain.
  (The Milestone-3 slice that preceded this reconciliation had a
  `knowledge_cache.py` binder against a since-superseded, non-Protocol
  Knowledge Service design — dropped along with that design, not carried
  forward as dead code.)
- The "lightweight, faster-turnaround approval track specific to market
  data" §9.7 leaves as a Milestone 3 implementation call. Not decided here:
  with no ingestion path there is nothing yet queuing for approval.
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
