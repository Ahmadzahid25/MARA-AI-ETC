# shared/auth

Who may act at which approval gate — [`10-human-in-the-loop.md`](../../docs/architecture/10-human-in-the-loop.md) §10.2.

## Why this is a module and not an `if` in the router

§10.2 gives each of the six Loan Assessment gates a different approver, and the difference *is* the control. A Finance Officer signing off a risk rating, or an officer acknowledging a compliance violation on the Compliance Officer's behalf, defeats the separation the gates exist to create.

Authentication does not give you this. A signed-in officer is authenticated for *some* gate, not for the one in front of them.

So the mapping is declared once, as data, and checked at the Gateway — same reasoning as [`shared/agent_profiles`](../agent_profiles/): a policy spread across call sites is one nobody can review as a whole, and one that drifts when only some sites are updated.

## The one rule that makes it work

**The pending gate is read from the workflow, never from the request.**

`services/api_gateway/routers/loans.py` calls `aget_state()` and takes the gate from the checkpointed interrupt. A client-supplied gate name would let a caller nominate whichever gate they happen to hold the role for — the control exactly inverted.

## Fails closed

`authorize_gate()` raises `KeyError` on a gate absent from `GATE_ROLES`. Adding a gate to a workflow without deciding who may approve it breaks at the first request rather than quietly accepting anyone. The router turns an unmapped gate into a 500 for the same reason: "anyone may approve this" is the one answer that must never be arrived at by default.

## Two places this is weaker than §10.2, on purpose

Both are recorded in `approval_gates.py` next to the mapping rather than left to be discovered by their absence:

- **`PUBLISH_APPROVAL` is not true dual control.** §10.2 says "Case owner + Committee Secretary" — two people. The workflow pauses once, so there is nowhere to collect a second signature. Currently checks the actor holds *one* of the two roles.
- **`RECOMMENDATION_APPROVAL` has no exposure threshold.** Escalation to Branch Manager is "above a configurable exposure threshold"; that threshold doesn't exist in config yet, so a Branch Manager is accepted at any exposure.

Both are widenings, not narrowings — they let through approvals §10.2 would gate further, and neither admits an approver §10.2 excludes outright.
