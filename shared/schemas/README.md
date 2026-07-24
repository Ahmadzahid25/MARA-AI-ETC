# Shared typed schemas (agent/tool I/O, events)

Implemented (Milestone 1, first slice): the document-extraction contract and
the common tool-error/audit-log types shared by every tool. Leaf module per
[03-repository-structure.md §3.3](../../docs/architecture/03-repository-structure.md#33-dependency-rules)
— depends on nothing else in this repo.

## Files

| File | Purpose |
|---|---|
| `documents.py` | `DocumentExtractionRecord`, `ExtractedField`, `Citation`, `BoundingBox`, `DocumentClassification`, `ExtractionSource` — the contract between the Document Agent (not yet built) and the Review & Approval Console (`apps/officer-workspace/`, see its own `AGENTS.md`) |
| `tooling.py` | `ToolError` taxonomy (`ToolInputError`, `ToolTimeoutError`, `ToolExternalServiceError`, `ToolPermissionError`) and `ToolInvocationLog`/`log_tool_invocation()` — the audit-log shape every tool call writes, per [06-tool-architecture.md §6.1](../../docs/architecture/06-tool-architecture.md) |

`log_tool_invocation()`'s default sink is structured logging, not a real
Audit Memory write — `services/audit_service` doesn't exist yet. See the
`TODO(milestone-1)` in `tooling.py`.

See [06-tool-architecture.md](../../docs/architecture/06-tool-architecture.md)
and [03-repository-structure.md#33-dependency-rules](../../docs/architecture/03-repository-structure.md#33-dependency-rules)
for the full specification. Do not add code here without a corresponding
entry in those documents, per docs/repo-audit/05-development-guidelines.md §5.5.
