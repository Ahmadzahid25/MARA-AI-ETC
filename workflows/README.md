# workflows/

Bounded, versioned LangGraph workflow **templates** — see [`docs/architecture/07-workflow-architecture.md`](../docs/architecture/07-workflow-architecture.md).

Every template follows the same eight-stage model: Start → Planning → Delegation → Execution → Validation → Approval → Completion → Audit (§7.1). The Planner agent *selects and parameterizes* one of these templates at runtime — it does not construct new graph topology (see [`docs/architecture/05-agent-architecture.md`](../docs/architecture/05-agent-architecture.md) §5.2.1). Any change to a template's node/edge shape is a reviewed, versioned code change here, never something produced dynamically by an LLM call.

`human_review/` is not independently triggered — it's the shared Approval-stage subgraph every other template reuses (§7.3), so approval behavior is defined once, not per workflow.
