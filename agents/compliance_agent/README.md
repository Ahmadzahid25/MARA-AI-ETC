# Compliance Agent

**Milestone-1 stub, pulled forward from its original Milestone 2 scope by
explicit decision** (see `agents/compliance_agent/compliance_agent.py`'s
module docstring for the full reasoning). Implemented: `ComplianceAgent.check_compliance()`
— checklist structure, hard-violation detection
(`ComplianceChecklist.has_hard_violation`), and the escalation shape per
[05-agent-architecture.md §5.4](../../docs/architecture/05-agent-architecture.md#54-compliance-agent).

**No real policy-matching logic.** `services/knowledge_service` (the
Dify-backed policy corpus) doesn't exist yet — still genuinely Milestone 2
scope. The default `policy_lookup` always returns no matches, so every check
currently resolves to `NO_POLICY_FOUND` — this is §5.4's own specified
"inconclusive lookup" behavior, not a fabricated shortcut. `policy_lookup`
and `checker` are injectable so Milestone 2 only has to supply real
implementations, not restructure this agent.

See [05-agent-architecture.md](../../docs/architecture/05-agent-architecture.md)
for the full specification. Do not add code here without a corresponding
entry in that document, per docs/repo-audit/05-development-guidelines.md §5.5.
