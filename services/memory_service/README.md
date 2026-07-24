# Memory service

**Long-term Memory calibration tracking implemented (Milestone 1),
governance-mandated** — the ACCB approval report accepts LLM self-reported
confidence as inherently uncalibrated (Review Board R-A5) "on condition
that the Long-term Memory calibration-tracking loop is actually built and
actively monitored from Milestone 1 onward, not treated as a nice-to-have"
([architecture-approval-report.md §5](../../docs/governance/architecture-approval-report.md)).

`calibration.py`: `write_calibration_event()` / `query_calibration_stats()`
against `long_term_memory_calibration` (append-only, one row per extracted
field per workflow — stated confidence vs. whether an officer corrected
it). `adapters.py`: `extraction_record_to_calibration_events()` turns a
`DocumentExtractionRecord` into that shape. Wired into
`workflows/document_assessment`'s confirm-extraction node — every real
assessment now emits calibration signal automatically, not as a
separately-triggered job.

**Not yet implemented:**
- The "periodic batch analysis" reporting layer feeding Phase 12
  observability ([08-memory-architecture.md §8.2](../../docs/architecture/08-memory-architecture.md)) —
  `query_calibration_stats()` is a live aggregate query for now, not a
  scheduled materialization.
- The other five memory kinds (Conversation, Task, Knowledge, Shared,
  Audit — Audit lives in `services/audit_service`) — this module is
  calibration tracking only so far.
- **`long_term_memory_calibration` table doesn't exist yet** — see
  `infrastructure/AGENTS.md` item 8 for the DDL handed to the developer who
  owns `infrastructure/compose/init/postgres-primary-init.sql`. Tested only
  against a mocked `asyncpg` pool.

See [08-memory-architecture.md](../../docs/architecture/08-memory-architecture.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
