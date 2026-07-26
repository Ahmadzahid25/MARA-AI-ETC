# Loan Assessment workflow template

Implemented (Milestone 4): `build_loan_assessment_graph()` — the reference
workflow from §7.2: Document → {Compliance, Finance, Market} → Risk →
Recommendation → `services/publishing_service`, assembled from every agent
built in Milestones 1–4. Five real, durable LangGraph `interrupt()`
approval gates (confirm extraction, financial sign-off, risk review,
recommendation approval, publish sign-off), plus a sixth, conditional one
(compliance hard-violation acknowledgment) — all exercised in
`tests/unit/mara/test_loan_assessment_workflow.py` against a real graph
execution (`InMemorySaver`), including the parallel Compliance/Finance/
Market fan-out and fan-in.

**Two real bugs this module's own tests caught, not merely asserted
away** — see the module's own docstring for the full account:
1. LangGraph's plain `add_edge()` fan-in does not wait for "all
   predecessors, whenever they finish" — it re-fires the join node once
   per superstep any predecessor's edge lands. Three branches of different
   hop-depth (compliance's extra acknowledgment hop vs. finance/market's
   single hop) fired the join, and everything after it, **twice**. Fixed
   with `_finance_join_node`/`_market_join_node`, trivial pass-through
   nodes that equalize hop-depth across all three branches.
2. A ledger-scoped citation-verification attempt (`ProvenanceLedger`)
   failed for a structural reason, not a test-fixture bug: this workflow
   takes each agent as a single, already-constructed instance reused
   across every node call, but ledger-scoped verification requires the
   *same* ledger to back both a closure's retrieval and its later
   verification — a mismatch this module's docstring documents rather than
   works around with a fake pass. Citation verification is consequently
   **not wired into this workflow slice**.

**A genuine, documented tension, not silently resolved either way:** an
*acknowledged* hard compliance violation still yields a withheld
recommendation, because `agents/recommendation_agent`'s own §5.8 escalation
rule is unconditional ("if any upstream agent flagged a hard compliance
violation") — §7.4's acknowledgment gate lets this workflow keep computing
Risk for audit-trail completeness, but does not itself grant Recommendation
an exception path §5.8 doesn't specify.

**Not yet wired**, matching every other agent/workflow's own "not yet
wired to the Agent Runtime" note in this repo: `agents/planner`'s template
selection (this graph is invoked directly with parameters already
decided, the same simplification `workflows/document_assessment` already
made), `services/supervisor_service`'s retry/circuit-breaker dispatch
policy (each node calls its agent directly), and a real Postgres
checkpointer (tested only against `InMemorySaver` — see
`infrastructure/AGENTS.md`'s "never tested against `postgres-primary`"
note, which applies here too).

See [07-workflow-architecture.md#72-reference-workflow--loan-assessment](../../docs/architecture/07-workflow-architecture.md#72-reference-workflow--loan-assessment)
for the full specification this module implements. Do not add code here
without a corresponding entry in that document, per
docs/repo-audit/05-development-guidelines.md §5.5.
