# agents/

MARA's 7 true domain agents — Planner, Document, Compliance, Finance, Risk, Market, Recommendation. Each is a configuration of the shared Agent Runtime (system prompt, allowed tools, memory scope, confidence threshold), not a bespoke codebase — see [`docs/architecture/05-agent-architecture.md`](../docs/architecture/05-agent-architecture.md) §5.1.

**That configuration lives in [`shared/agent_profiles/`](../shared/agent_profiles/), not in the agent module.** Tool grant, autonomy level, confidence floor, approval gate, and egress are declared once in the registry and read back here:

```python
PROFILE = profile_for(AgentName.DOCUMENT.value)
CONFIDENCE_THRESHOLD = confidence_threshold_for(AgentName.DOCUMENT.value)
```

Declaring a threshold or tool list as a constant in the agent instead puts it out of reach of the invariants CI enforces (sole egress, no external-transmission tool in any grant, every decision-bearing agent has a confidence floor). See §5.15 for the four dials and what widening each one costs.

**Not everything that sounds like an "agent" belongs here.** Supervisor, the merged Publishing service, Voice, and Audit were reclassified as deterministic services (§5.10–5.11) and live in [`services/`](../services/) instead. Before adding a new component here, apply the test in §5.14: does it make a genuinely ambiguous judgment call, or a deterministic transformation? Only the former goes in `agents/`.

Not to be confused with `.agents/`, `.openhands/microagents/`, or root `skills/` — see the naming-disambiguation table in [`AGENTS.md`](../AGENTS.md) or [`docs/repo-audit/03-target-structure.md`](../docs/repo-audit/03-target-structure.md) §3.3.
