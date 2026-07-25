# shared/agent_profiles

The one place agent autonomy is declared. If you are widening or narrowing what an agent may do, you edit [`profiles.py`](profiles.py) and nothing else.

See [`docs/architecture/05-agent-architecture.md`](../../docs/architecture/05-agent-architecture.md) §5.15 for the governance rule this registry is subject to, and §5.1 for the common agent contract it encodes.

## Why this exists

Before this module, one permission relationship was written down twice, in opposite directions, with nothing checking they agreed:

```python
# agents/document_agent/document_agent.py — decorative, enforced nowhere
allowed_tools = ('ocr', 'pdf_parse', 'document_classification')

# tools/ocr/ocr_tool.py — the real check
ALLOWED_CALLERS = frozenset({'document_agent'})
```

Widening one agent's grant meant editing every tool it touches plus the agent, and the two halves could drift apart silently. Confidence thresholds had the same shape — module constants next to whichever agent used them.

Now the grant is declared once and the tool side is *derived* from it:

```python
# tools/ocr/ocr_tool.py
ALLOWED_CALLERS = callers_allowed_for_tool(TOOL_NAME)
```

## The four dials

Each is independent on purpose — they are different risks, and conflating them is what makes autonomy hard to adjust incrementally later.

| Dial | Field | What widening it costs |
|---|---|---|
| **Reach** | `allowed_tools` | More surface a prompt-injected agent could reach for. Every tool added here must already exist in [`06-tool-architecture.md`](../../docs/architecture/06-tool-architecture.md) §6.2 with a reviewed permission scope. |
| **Latitude** | `autonomy` | `BOUNDED` → `GUIDED` lets the agent choose tool order for itself. Cheap relative to the others: the grant and the approval gate are unchanged. |
| **Escalation floor** | `confidence_threshold` | Lowering it means fewer outputs get a human look. This is the dial that quietly trades away oversight — treat a change here as a policy change, not a tuning change. |
| **Gate** | `approval` | `ALWAYS` → `ON_LOW_CONFIDENCE` → `NONE`. Never loosen this for a decision-bearing agent without the approval path in [`10-human-in-the-loop.md`](../../docs/architecture/10-human-in-the-loop.md) being re-reviewed. |

Two fields are not dials — they are invariants that happen to live here:

- `external_egress` — true for the Market Agent alone (§5.7). A second egress path is what §11.7's network policy exists to prevent; the test suite pins this.
- `can_inform_decision` — false only for the exploration sandbox. Setting it false is what *buys* the freedom on the other four dials.

## Recommended way to give an agent more freedom

In order of increasing cost, stop at the first that solves your problem:

1. **`BOUNDED` → `GUIDED`.** The agent picks its own tool order inside the grant it already has. Nothing else changes — same reach, same floor, same gate. This is the intended default step once the Agent Runtime's action/observation loop lands.
2. **Add a tool to `allowed_tools`.** The tool-side allow-list follows automatically.
3. **Use the exploration sandbox.** For open-ended analysis where you genuinely want a broad agentic loop, `EXPLORATION_SANDBOX` already has `EXPLORATORY` autonomy and no confidence gate — affordable precisely because `can_inform_decision=False` bars its output from the decision path.

What is *not* on this list: lowering a decision-bearing agent's confidence floor or loosening its approval gate to make it feel more capable. Those trade away the oversight guarantees in [`01-vision.md`](../../docs/architecture/01-vision.md), and the registry deliberately makes them look like what they are.

## The invariants CI enforces

[`tests/unit/mara/test_agent_profiles.py`](../../tests/unit/mara/test_agent_profiles.py) fails the build if any of these stop holding:

- Every one of the seven true agents has a profile, and resolves its model tier from `shared/llm/model_tiers.py` rather than overriding it here.
- The Market Agent is the only profile with `external_egress`, and `web_search` is granted to it alone.
- No profile holds an external-transmission tool (§6.3 — the capability must not exist inside any grant).
- Any profile at `EXPLORATORY` autonomy has `can_inform_decision=False`.
- Every decision-bearing profile declares a confidence floor.
- The implemented tools' allow-lists match what the registry grants.

## Adding a profile

A new profile needs, before it is merged: a corresponding entry in `05-agent-architecture.md` (per `docs/repo-audit/05-development-guidelines.md` §5.5), every tool in its grant already catalogued in §6.2, and — if it is not one of the seven true agents — `can_inform_decision=False`, since §5.14's agent-vs-service test is what decides whether something belongs on the decision path at all.
