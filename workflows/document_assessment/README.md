# Document Assessment workflow template

Implemented (Milestone 1): `build_document_assessment_graph()` — a real
LangGraph `StateGraph`: `document_extraction` (Document Agent) →
`validation` (confidence check) → `confirm_extraction` (a real durable pause
via `langgraph.types.interrupt()`, resumed with `Command(resume=...)`) →
`compliance_check` (Compliance Agent, only on approval) → `completion`. Per
[07-workflow-architecture.md §7.3](../../docs/architecture/07-workflow-architecture.md#73-workflow-catalogue)'s
catalogue entry.

Start/Planning/Delegation (the Planner/`supervisor_service` stages of the
common 8-stage model, §7.1) are collapsed — those components don't exist
yet. This template is invoked directly with its parameters already decided.
A rejected extraction currently routes to `completion` without an automatic
targeted re-run — see the module docstring for why that's a deliberate,
named simplification rather than a silently dropped requirement.

See [07-workflow-architecture.md](../../docs/architecture/07-workflow-architecture.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
