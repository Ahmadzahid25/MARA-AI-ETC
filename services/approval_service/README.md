# Approval service

Implemented (Milestone 1): `confirm_extraction()` — the Document Assessment
workflow's "confirm extraction" gate. Resumes a paused
`workflows.document_assessment` graph via a real LangGraph
`Command(resume=...)`, per
[10-human-in-the-loop.md §10.5](../../docs/architecture/10-human-in-the-loop.md)'s
three-action model (Approve / Reject / **Correct** — not just two). A
Correct decision's field corrections are recorded as a distinct,
attributed `ApprovalRecord` and reach the workflow's `extraction_record` for
real (verified in `tests/unit/mara/test_approval_service.py`'s end-to-end
integration test against a real compiled workflow graph, not just a mock).

Does **not** import `workflows/` directly (dependency rule,
[03-repository-structure.md §3.3](../../docs/architecture/03-repository-structure.md#33-dependency-rules))
— takes any object with an `ainvoke()` method (a `ResumableWorkflow`
protocol), so the caller supplies the actual compiled graph.

Audit logging: `confirm_extraction()` accepts an optional async
`audit_writer` — when supplied (as `services/api_gateway/composition.py`
now does, binding `services/audit_service.write_audit_event` to a real
connection pool), it takes priority and every decision is genuinely written
to the `audit_memory` table, not just logged. Falls back to the same
interim structured-logging stub as `shared/schemas/tooling.py` when no
writer is given (e.g. in tests that don't need a real database).

See [10-human-in-the-loop.md](../../docs/architecture/10-human-in-the-loop.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
