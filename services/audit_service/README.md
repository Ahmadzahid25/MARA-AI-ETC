# Audit service

**Pulled forward from Milestone 5 to Milestone 1 by explicit decision**
(originally scoped in `docs/architecture/14-roadmap.md` §14.7 — "Voice and
audit completeness"). Implemented now: `write_audit_event()` and
`query_audit_events()` against the `audit_memory` table already defined in
`infrastructure/compose/init/postgres-primary-init.sql` (partitioned,
append-only — see [08-memory-architecture.md §8.2](../../docs/architecture/08-memory-architecture.md)),
plus `adapters.approval_record_to_audit_event()` mapping
`services/approval_service`'s `ApprovalRecord` into the table's shape. This
is the real write path behind `services/approval_service`'s
`confirm_extraction(audit_writer=...)` parameter, wired end-to-end through
`services/api_gateway/composition.py`.

**Not implemented yet:**
- The optional LLM narrative-summarization layer
  ([05-agent-architecture.md §5.11.3](../../docs/architecture/05-agent-architecture.md#5113-audit-service-formerly-audit-agent))
  — the structured query API is the "primary, authoritative" output this
  slice delivers; narrative summary is a thin layer on top, not a
  precondition.
- Real writes from `tools/ocr` and `tools/documents`' tool-call audit log
  (`shared/schemas/tooling.py`'s `log_tool_invocation`) — those call sites
  are synchronous by design (their own timeout enforcement), while this
  service's write path is `asyncpg`-only (async-only). Bridging that gap is
  a deliberate follow-up, not silently worked around — see the comment in
  `shared/schemas/tooling.py::_default_sink`.
- **Never run against a real Postgres instance** — tested only against a
  mocked `asyncpg` pool (no Docker in this environment). See
  `infrastructure/AGENTS.md` for the verification this needs once the
  Docker stack is up.

See [05-agent-architecture.md](../../docs/architecture/05-agent-architecture.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
