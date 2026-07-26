# Finance Agent

Implemented (Milestone 3): `FinanceAgent.analyze()` — runs deterministic
calculations (`tools/calculations`) over Document Agent extraction fields,
traces every resulting figure back to either its source citation
(`EXTRACTED`) or the specific formula ID/version that produced it
(`CALCULATED`, `shared/schemas/finance.py`'s `FinancialFigure`), then
produces a qualitative repayment-capacity assessment as the one genuinely
agentic step (Sonnet-tier LLM call, injectable `assessor` for tests).

Per §5.5's escalation rule, a required source field that's missing or
below the Document Agent's 0.85 confidence threshold raises
`MissingSourceFigureError` rather than computing on unverified input — the
owning workflow is responsible for turning that into an officer
escalation, the same pattern `agents/document_agent` uses for low-confidence
fields.

Product-terms lookup goes through the real Milestone-2 Knowledge Service
boundary — `services.knowledge_service.contract.KnowledgeBackend` /
`tools.rag.rag_tool.rag_query`, the same seam
`agents/compliance_agent/policy_lookup.py` uses — not an invented shape.
Citations returned are `PolicyCitation` (versioned knowledge-corpus
clauses), never `Citation` (which points at a page of the applicant's own
document). Still depends on a real `KnowledgeBackend` being wired (Dify is
deployed at the infra level; the Python adapter implementing
`KnowledgeBackend.retrieve()` against it doesn't exist yet — see
`services/knowledge_service/README.md`) to return anything other than
`KnowledgeBackendNotConfiguredError`.

See [05-agent-architecture.md#55-finance-agent](../../docs/architecture/05-agent-architecture.md#55-finance-agent)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
