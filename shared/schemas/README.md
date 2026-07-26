# Shared typed schemas (agent/tool I/O, events)

Implemented (Milestone 1, first slice): the document-extraction contract and
the common tool-error/audit-log types shared by every tool. Leaf module per
[03-repository-structure.md §3.3](../../docs/architecture/03-repository-structure.md#33-dependency-rules)
— depends on nothing else in this repo.

## Files

| File | Purpose |
|---|---|
| `documents.py` | `DocumentExtractionRecord`, `ExtractedField`, `Citation`, `BoundingBox`, `DocumentClassification`, `ExtractionSource` — the contract between the Document Agent and the Review & Approval Console (`apps/officer-workspace/`, see its own `AGENTS.md`) |
| `compliance.py` | `ComplianceChecklist`, `ComplianceChecklistItem`, `ComplianceStatus` — the Compliance Agent's output contract |
| `knowledge.py` | `RetrievalQuery`, `RetrievalFilters`, `RetrievalResult`, `RetrievedChunk`, `PolicyCitation`, `DocumentKind`, `SensitivityClass` — the Knowledge Memory retrieval contract between `services/knowledge_service`'s `KnowledgeBackend` protocol and `tools/rag` (Milestone 2) |
| `finance.py` | `FinancialAnalysis`, `FinancialFigure`, `FigureProvenance` — the Finance Agent's output contract; every figure is schema-enforced as either `EXTRACTED` (with a source citation) or `CALCULATED` (with a formula ID/version), never neither (Milestone 3) |
| `market.py` | `MarketBrief`, `MarketClaim` — the Market Agent's output contract; every claim carries its source URL and retrieval date directly (Milestone 3) |
| `risk.py` | `RiskRating`, `RiskStatus` — the Risk Agent's output contract, including the incomplete/escalated states §5.6 requires (Milestone 3) |
| `planning.py` | `PlanResult`, `WorkflowTemplate` — the Planner's output contract; `PlanResult.is_escalated` is `True` exactly when `template_name` is `None` (Milestone 4) |
| `recommendation.py` | `RecommendationOutput`, `RecommendationDecision` — the Recommendation Agent's output contract; `decision` and `withheld_reason` are schema-enforced as mutually exclusive (Milestone 4) |
| `tooling.py` | `ToolError` taxonomy (`ToolInputError`, `ToolTimeoutError`, `ToolExternalServiceError`, `ToolPermissionError`) and `ToolInvocationLog`/`log_tool_invocation()` — the audit-log shape every tool call writes, per [06-tool-architecture.md §6.1](../../docs/architecture/06-tool-architecture.md) |

`log_tool_invocation()`'s default sink is structured logging, not a real
Audit Memory write. `services/audit_service` now exists (pulled forward
from Milestone 5) and is wired as the real writer for approval decisions —
but not yet for tool-call logging here, due to a sync/async mismatch
between this module's sync `AuditSink` and `audit_service`'s `asyncpg`-only
write path. See the comment on `_default_sink` in `tooling.py` and
`services/audit_service/README.md`.

See [06-tool-architecture.md](../../docs/architecture/06-tool-architecture.md)
and [03-repository-structure.md#33-dependency-rules](../../docs/architecture/03-repository-structure.md#33-dependency-rules)
for the full specification. Do not add code here without a corresponding
entry in those documents, per docs/repo-audit/05-development-guidelines.md §5.5.
