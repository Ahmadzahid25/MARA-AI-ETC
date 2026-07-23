# MARA AI-ETC Architecture Approval Report

**Issued by:** MARA AI-ETC Architecture Change Control Board (ACCB)
**Reviewing:** [docs/architecture/00-INDEX.md](../architecture/00-INDEX.md) (master plan), [docs/architecture/review/00-review-index.md](../architecture/review/00-review-index.md) (independent review board critique), [docs/repo-audit/00-index.md](../repo-audit/00-index.md) (repository audit and restructuring plan)
**Action taken:** none. This board writes decisions; it does not implement them. No file outside this report was modified to produce it.

---

## Status update — Architecture Baseline v1.0

Following this report, [docs/architecture/00-INDEX.md](../architecture/00-INDEX.md) was published as **Architecture Baseline v1.0**, merging the closeable conditions below directly into the master plan's phase documents (full changelog in the baseline's own index). Status as of that publication:

| Item | Status | Evidence |
|---|---|---|
| Condition C-1 (docs taxonomy) | **CLOSED** | [repo-audit/03-target-structure.md](../repo-audit/03-target-structure.md) and [architecture/03-repository-structure.md](../architecture/03-repository-structure.md) both now specify `{architecture/, repo-audit/, governance/, security/, deployment/, api/, policy/}` |
| Condition C-2 (merge review findings into master plan) | **CLOSED** | All six items merged — see the Baseline v1.0 changelog in [architecture/00-INDEX.md](../architecture/00-INDEX.md) — Planner/§5.2.1, citation verification/§6.1, extraction-not-fork/§4.1–4.2, agent→service reclassification/§5.10–5.14, model-tiering/§4.6.1 |
| Condition C-3 (`enterprise/` removal PR) | **STILL OPEN** | This is a repository action (deleting files, opening a PR), not a documentation change — outside the scope of a documentation baseline update. Tracked in [repo-audit/04-migration-plan.md](../repo-audit/04-migration-plan.md) Phase 1–2, still pending execution. |
| Condition C-4 (legal sign-off on licensing) | **STILL OPEN** | Outside engineering's authority to close by any documentation change. Tracked in `docs/policy/` per [architecture/11-security-architecture.md](../architecture/11-security-architecture.md) §11.7. |
| Condition C-5 (Dify database separation decision) | **CLOSED** | [architecture/09-knowledge-architecture.md](../architecture/09-knowledge-architecture.md) §9.1.1 now states the decision explicitly: separate database instance |
| Mandatory Change 1 (Market Agent query sanitization + network-policy egress) | **CLOSED (specified)** | [architecture/06-tool-architecture.md](../architecture/06-tool-architecture.md) §6.6, [architecture/11-security-architecture.md](../architecture/11-security-architecture.md) §11.7, [architecture/05-agent-architecture.md](../architecture/05-agent-architecture.md) §5.7.1. Specified, not yet implemented or tested — [architecture/14-roadmap.md](../architecture/14-roadmap.md) Milestone 3 acceptance criteria now require a red-team test confirming this before that milestone is considered done. |
| Mandatory Change 2 (market-cache approval gate) | **CLOSED (specified)** | [architecture/09-knowledge-architecture.md](../architecture/09-knowledge-architecture.md) §9.7. Same caveat as above — specified in the baseline, verified at Milestone 3. |

"Closed" above means **the documentation now reflects the corrected, binding decision** — it does not mean the corresponding code exists yet, since no implementation has started. Milestone 0's acceptance criteria ([architecture/14-roadmap.md](../architecture/14-roadmap.md) §14.2) still require C-3 to be independently verified as merged before Milestone 0 itself is considered complete; this status table is not a substitute for that check.

---

## 1. Executive Decision

# APPROVED WITH CONDITIONS

The architecture is technically realistic, appropriately scoped, and grounded in an actual inventory of the repository rather than an idealized one — this board does not send it back for redesign. It is not given unconditional approval because three of this board's prior work products (the review board's critical findings, the repo audit's documentation fixes, and a taxonomy question raised in this very approval request) currently exist only as *recommendations in separate documents*, not as changes reflected in the master plan itself. An architecture whose safety-relevant corrections live only in a review file, un-merged into the source of truth a developer would actually read first, is not yet approved for implementation — it is approved *pending the paperwork catching up to the decisions already made*. Section 3 is the specific, closeable list.

---

## 2. Approved Decisions

### Decision 1 — Remove OpenHands commercial SaaS components (`enterprise/`)

**APPROVE.** This is not a new finding for this board to weigh — it is the repo audit's own Critical finding (P-01, [repo-audit/02-problems-found.md](../repo-audit/02-problems-found.md)), independently arrived at from direct inspection of `enterprise/`'s contents (billing, a hosted-multi-tenant Keycloak realm template, its own isolated dependency tree). Undefended surface with zero MARA function in a system whose own threat model is built around minimizing exactly that. No condition attached beyond what the repo audit's Migration Plan Phase 2 already specifies.

### Decision 2 — `openhands/app_server/` as primary integration point; `openhands/server/` as legacy/reference only

**APPROVE.** Grounded in `app_server/README.md`'s own stated scope ("V1 integration"), not an assumption — this board confirms the repo audit read that correctly. Condition (minor, tracked in Section 3, not blocking): this determination should be re-confirmed if upstream OpenHands materially changes either module's status, since the entire justification rests on upstream's *current* stated direction, not a permanent architectural fact.

### Decision 3 — `docs/` as canonical documentation root

**APPROVE WITH A TAXONOMY CORRECTION.** `docs/` over `documentation/` is approved and already correctly reconciled in [repo-audit/03-target-structure.md](../repo-audit/03-target-structure.md) §3.1 against the master plan's original Phase 3. However: this request's proposed subfolder set (`architecture/`, `repo-audit/`, `security/`, `deployment/`, `api/`) is not the same set the repo audit already specified (`architecture/`, `repo-audit/`, `runbooks/`, `api/`, `policy/`), and this board will not silently pick one over the other. Specifically flagged: this request's list **drops `policy/`**, which the master plan's own Phase 11 ([architecture/11-security-architecture.md](../architecture/11-security-architecture.md) §11.4) requires for PDPA/compliance documentation — that is not a folder this board will let quietly disappear because a later prompt's example omitted it. **Approved canonical taxonomy:** `docs/{architecture/, repo-audit/, security/, deployment/, api/, policy/}` — `security/` is accepted as a genuinely useful addition (threat models, red-team records, third-party assessment reports — distinct from `policy/`'s PDPA/compliance-documentation role), and `deployment/` is accepted as the renamed home for what the repo audit called `runbooks/` (deployment guides and operational runbooks belong together). This merge is Condition C-1 in Section 3.

### Decision 4 — Reuse `openhands-ui/` as the frontend design foundation; no separate frontend framework

**APPROVE WITH A CLARIFICATION, not a contradiction.** This board confirms the repo audit's finding ([repo-audit/03-target-structure.md](../repo-audit/03-target-structure.md) §3.2) that `openhands-ui/` is a genuinely reusable, self-contained design-system package, and endorses reusing it. The clarification needed: "do not create a separate frontend framework" must not be read as "reuse `frontend/`'s existing screens" — the architecture review board already rejected that specifically (reskinning a coding-agent IDE UI into an officer review console, [architecture/review/01-architecture-and-foundation-review.md](../architecture/review/01-architecture-and-foundation-review.md) §2.1). What is approved, precisely: **same framework/toolchain and same design-system (`openhands-ui/`), new application (`apps/officer-workspace/`)** — one design language, two apps, not one framework forked into two incompatible UIs and not two different frameworks. This is already exactly what the repo audit's target structure specifies; this decision is approved as consistent with it, not as a separate instruction.

### Decision 5 — No generic monorepo restructuring; preserve OpenHands native structure; add MARA extensions alongside

**APPROVE, unconditionally.** This is the repo audit's own central finding and rationale ([repo-audit/03-target-structure.md](../repo-audit/03-target-structure.md) §3.1), independently justified against the specific operational cost of breaking upstream mergeability. This board adds nothing beyond endorsing it — it is the correct call and this request's example template (a generic `apps/`/`core/`/`packages/` nesting of everything, including `openhands/` itself) was already correctly and explicitly rejected by the audit for exactly this reason.

---

## 3. Conditions Before Implementation

These are process gates — they must be *closed*, not merely acknowledged, before Milestone 0 (Foundation) work begins in earnest. Each has an owner and a concrete "done" test, not just a description.

| ID | Condition | Done when | Blocks |
|---|---|---|---|
| C-1 | Adopt the reconciled `docs/` taxonomy from Decision 3 above (`architecture/, repo-audit/, security/, deployment/, api/, policy/`) as the single canonical structure, superseding both the repo audit's original proposal and this request's Decision 3 as separately stated | [repo-audit/03-target-structure.md](../repo-audit/03-target-structure.md) is edited to match | Any new `docs/` content being written into a folder name that later has to be renamed |
| C-2 | Merge the review board's Critical findings ([architecture/review/05-mvp-and-final-decision.md](../architecture/review/05-mvp-and-final-decision.md) §12.2, items 1–6) into the actual master plan documents they correct — Planner bounded-template constraint into [architecture/05-agent-architecture.md](../architecture/05-agent-architecture.md) §5.2 and [architecture/07-workflow-architecture.md](../architecture/07-workflow-architecture.md); citation verification into [architecture/06-tool-architecture.md](../architecture/06-tool-architecture.md); OpenHands extraction-not-fork scope into [architecture/04-technology-stack.md](../architecture/04-technology-stack.md) and [architecture/03-repository-structure.md](../architecture/03-repository-structure.md); the agent→service reclassification into [architecture/05-agent-architecture.md](../architecture/05-agent-architecture.md); the Dify database-separation decision into [architecture/09-knowledge-architecture.md](../architecture/09-knowledge-architecture.md); the model-tiering strategy into [architecture/04-technology-stack.md](../architecture/04-technology-stack.md) §4.6 | The master plan reads correctly on its own, with no need to cross-reference the review document to know what's actually approved | Milestone 1 implementation start — a developer building against the master plan today would build the ambiguous/reclassified version, not the corrected one |
| C-3 | Execute repo audit Migration Plan Phase 1 (documentation cleanup) and the `enterprise/`-removal half of Phase 2, as already recommended in [repo-audit/07-final-output-summary.md](../repo-audit/07-final-output-summary.md) §6 | That PR is merged | Any external-facing review of the repository (including the Milestone 6 security assessment eventually needing to explain, rather than simply not contain, a leftover SaaS billing module) |
| C-4 | MARA legal/procurement sign-off recorded on OpenHands `LICENSE` terms and `CITATION.cff` attribution obligations for a government derivative work (repo audit P-13) | A written record exists, referenced from `docs/policy/` | Formal government security/procurement review (Milestone 6) — this is exactly the kind of open item that stalls a late-stage review if first raised there instead of now |
| C-5 | Explicit, written decision on whether Dify's operational database is a separate instance from the platform's primary Postgres (review board Finding C2), recorded in [architecture/09-knowledge-architecture.md](../architecture/09-knowledge-architecture.md) | The document states one answer, not "to be decided" | Milestone 2 (Knowledge Service) start |

---

## 4. Mandatory Changes

These are the two review-board Critical findings that specifically gate a *later* milestone (Market Agent, Milestone 3) rather than Milestone 0/1 — listed separately from Section 3 because they do not block starting implementation, only reaching that specific point in it. Both were already identified in [architecture/review/03-data-and-security-review.md](../architecture/review/03-data-and-security-review.md) and are reaffirmed here as binding, not optional, by this board:

1. **Query-sanitization enforcement on the Market Agent's external search tool**, verified programmatically at the Tool Runtime — not agent-prompted, not deferred to "the agent should know not to include PII" — plus network-policy-level enforcement restricting external egress to that tool's pod specifically (Finding B3). Absence of this is an active PDPA exposure the moment the Market Agent ships, not a theoretical one.
2. **Market-data caching into Knowledge Memory routed through the same document-lifecycle approval gate every other knowledge-base content type requires**, or explicitly and mechanically segregated into a lower-trust retrieval tier agents must treat differently (Finding C3) — closing the inconsistency the master plan itself introduced between §9.6 and §9.7 of [architecture/09-knowledge-architecture.md](../architecture/09-knowledge-architecture.md).

Neither of these requires new design work — the fix is already specified in the review. What's mandatory is that it actually lands in the Market Agent's implementation, not just in a document about the Market Agent.

---

## 5. Risks Accepted

The board accepts the following as ongoing, managed risks rather than blockers — each has a stated mitigation already in the plan, and this board is recording that "accepted with mitigation" is a deliberate decision, not an oversight:

- **LLM self-reported confidence is not inherently well-calibrated** (review board R-A5). The escalation mechanism that makes human-in-the-loop scale depends on it. Accepted, on condition that the Long-term Memory calibration-tracking loop ([architecture/08-memory-architecture.md](../architecture/08-memory-architecture.md) §8.2) is actually built and actively monitored from Milestone 1 onward, not treated as a nice-to-have.
- **Single Postgres instance at MVP scale**, with Audit Memory partitioning as the only near-term mitigation (Finding C1). Accepted for pilot scale (10–100 officers); explicitly *not* accepted at 1000-officer/multi-department scale without the row-level security work (Finding D3) — see [architecture/review/04-compliance-scale-cost-review.md](../architecture/review/04-compliance-scale-cost-review.md).
- **OpenHands upstream integration effort may be underestimated** (R-T1). Accepted; mitigated by Milestone 0 being explicitly scoped as a technical spike against `app_server/event` and `sandbox` internals before any agent depends on the fork being stable.
- **Officer adoption/trust is unproven** (R-B1). Accepted as inherent to any human-in-the-loop system being introduced into an existing manual process; mitigated by measuring officer-reported trust explicitly from Milestone 4, not inferring it from usage volume alone.
- **LLM cost before model-tiering is fully tuned** (Section 2, Decision-4-adjacent; [architecture/review/04-compliance-scale-cost-review.md](../architecture/review/04-compliance-scale-cost-review.md) §10.2). Accepted for MVP v1's single-agent scope; mitigated by cost tracking being live from Milestone 0, not added retroactively once costs are already a problem.

---

## 6. Next Development Phase

**Recommended: Milestone 0 — Foundation**, as already named in [architecture/14-roadmap.md](../architecture/14-roadmap.md) §14.2, with its acceptance criteria explicitly expanded to close every Condition in Section 3 and produce the eight artifacts this gate requires:

1. **Platform foundation** — the extracted `openhands/app_server/` integration boundary (event stream, sandbox, MCP host, secrets, user auth) wired up as a stable internal dependency, per [repo-audit/06-openhands-protection-rules.md](../repo-audit/06-openhands-protection-rules.md) §6.2–6.3, with the compatibility test from §6.4 (`git merge upstream/main` without reverting MARA work) passing on day one.
2. **Service boundaries** — `agents/` and `services/` scaffolded per the corrected classification from Condition C-2 (7 agents, not 12), with empty-but-real module structure per [repo-audit/03-target-structure.md](../repo-audit/03-target-structure.md).
3. **Agent framework** — the CrewAI-pattern agent-definition shape (role/goal/tools) running as LangGraph nodes, with the Planner constrained to bounded template selection from day one (Condition C-2), not built first and constrained later.
4. **LLM gateway** — the LiteLLM-based provider abstraction with the model-tiering routing rule from [architecture/04-technology-stack.md](../architecture/04-technology-stack.md) §4.6 (as corrected by C-2) implemented as actual routing logic, not left as a documented intention.
5. **MCP tools** — the tool registry live, with the first real tool (OCR, per Milestone 1's actual scope) registered through it end-to-end.
6. **Database architecture** — Postgres schema for the six memory kinds, with Audit Memory table partitioning present from the first migration (not retrofitted), and the Dify database-separation decision (Condition C-5) implemented, not just documented.
7. **API contracts** — typed request/response schemas at the Gateway and typed tool I/O schemas (per [architecture/06-tool-architecture.md](../architecture/06-tool-architecture.md)) established as the pattern before the first agent is built against them.
8. **Frontend integration** — `apps/officer-workspace/` scaffolded, consuming `packages/event-stream-client/` (extracted per [repo-audit/04-migration-plan.md](../repo-audit/04-migration-plan.md) Phase 3) and `packages/openhands-ui/`, per the clarified Decision 4 above.

This board will not treat Milestone 0 as complete, and will not clear Milestone 1 to begin, until Section 3's five conditions show as closed against the criteria stated in that table — not against a verbal confirmation that they've been considered.
