# Planner

Implemented (Milestone 4): `Planner.plan()` — matches an officer's
free-text objective against `KNOWN_TEMPLATES` (the eight bounded templates
from §7.3, verbatim) and returns a `PlanResult`: a template name +
parameters, or an escalation with a clarification question (§5.2's
0.75 confidence threshold). Template matching is the one genuinely agentic
step (Haiku-tier LLM call, injectable `matcher` for tests); parameter
validation against the selected template's `required_parameters` is
deterministic and happens regardless of whether the matcher was real or
injected.

**Not yet wired to dispatch a workflow instance.** Selecting a template is
this agent's whole job (§5.2.1) — actually invoking `workflows/
document_assessment` or `workflows/loan_assessment` with the selected
parameters is API Gateway / `services/supervisor_service` integration
work, the same "not yet wired to the Agent Runtime" gap every other agent
in this repo documents about itself (see `agents/document_agent`'s
README).

See [05-agent-architecture.md#52-planner](../../docs/architecture/05-agent-architecture.md#52-planner)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
