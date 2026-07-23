« [Index](00-INDEX.md) | Phase 14 of 16 »

# Phase 14 — Development Roadmap

> **v1.0 note:** per the [ACCB approval report](../governance/architecture-approval-report.md) §6, Milestone 0's acceptance criteria now explicitly include closing Conditions C-1, C-2, C-3, and C-5 — this milestone is not "complete" on infrastructure grounds alone. Agent counts below are corrected to 7 agents + 5 services throughout ([05-agent-architecture.md](05-agent-architecture.md) §5.14).

## 14.1 Staging philosophy

Each milestone ships something an officer can actually use, per [01-vision.md](01-vision.md)'s constraint that the full system shouldn't be a prerequisite for any value — and each milestone deliberately proves one architectural risk (per [15-risk-assessment.md](15-risk-assessment.md)) before the next milestone builds on top of it, rather than building all 7 agents in parallel against unproven foundations.

## 14.2 Milestone 0 — Foundation

| | |
|---|---|
| Objective | Stand up the extracted-OpenHands substrate, core infra, and security baseline before any MARA-specific agent exists — and close every ACCB gate condition closeable through engineering work |
| Features | Gateway + auth (Keycloak) wired to `app_server/user_auth`; Postgres/pgvector/Redis/MinIO provisioned (Dify on its own separate database instance, per ACCB Condition C-5 / [09-knowledge-architecture.md](09-knowledge-architecture.md) §9.1.1); LangGraph checkpointer configured against Postgres; CI (GitHub Actions) running lint/unit tests on the extended repo; observability stack (OTel, Prometheus, Grafana, Loki, Langfuse) deployed to dev/staging; `docs/` taxonomy finalized (ACCB Condition C-1); `enterprise/` removed (ACCB Condition C-3, [repo-audit/04-migration-plan.md](../repo-audit/04-migration-plan.md) Phase 1–2) |
| Dependencies | None — this is the base every later milestone depends on |
| Deliverables | Deployable skeleton system with authenticated login, empty workspace UI (`apps/officer-workspace/`), no agents yet |
| Risks | Underestimating OpenHands extraction integration effort (see [15-risk-assessment.md](15-risk-assessment.md) R-T1) |
| Acceptance criteria | An officer can log in via SSO, see an empty workspace, and a synthetic end-to-end trace (Gateway → dummy workflow → Postgres checkpoint) is visible in Grafana/Langfuse; **AND** ACCB Conditions C-1, C-2, C-3, C-5 show closed against the criteria in [governance/architecture-approval-report.md](../governance/architecture-approval-report.md) §3 (C-4, MARA legal sign-off, is tracked but does not block this milestone's technical completion since it is outside engineering's authority to close) |
| Complexity | High (integration-heavy, low novel logic) |

## 14.3 Milestone 1 — First agent, first workflow, first approval

| | |
|---|---|
| Objective | Prove the full agent → tool → approval → audit pattern end-to-end with the simplest possible agent, before investing in the other six |
| Features | Document Agent (OCR + PDF parse tools only); Document Assessment workflow (Phase 7); Approval Service with the "confirm extraction" gate; Audit Memory writes from Tool Runtime and Approval Service |
| Dependencies | Milestone 0 |
| Deliverables | An officer can upload a document, see extracted fields with confidence scores and citations, correct/approve them, and query the resulting audit trail |
| Risks | OCR accuracy on real MARA document formats/quality lower than assumed (R-A1); establishes the confidence-threshold tuning process needed by every later agent |
| Acceptance criteria | Meets [01-vision.md](01-vision.md)'s ≥90% extraction accuracy target on a sampled test set; 100% of extraction claims carry a citation; a correction is fully attributable in Audit Memory |
| Complexity | Medium |

## 14.4 Milestone 2 — Knowledge base and policy-aware compliance

| | |
|---|---|
| Objective | Stand up the Knowledge Service (Dify-backed, Phase 9) and the first agent that reasons over it |
| Features | Knowledge ingestion pipeline + document lifecycle/approval (Phase 9); Compliance Agent (Phase 5); RAG tool (Phase 6) |
| Dependencies | Milestone 1 (reuses Document Agent extraction as Compliance Agent input) |
| Deliverables | Policy corpus ingested and versioned; Compliance Agent produces a cited pass/fail/exception checklist against real MARA policy documents |
| Risks | Policy corpus completeness/quality gaps surfacing as "no applicable policy found" more often than expected (R-A2); chunking strategy needing tuning for MARA's specific document structure |
| Acceptance criteria | Compliance checklist citations are independently verifiable by a Compliance Officer against the source policy; a superseded-policy staleness check correctly flags an outdated citation in a test scenario |
| Complexity | Medium-High |

## 14.5 Milestone 3 — Financial and risk reasoning core

| | |
|---|---|
| Objective | Add the deterministic-calculation and synthesis agents that form the analytical core of a loan assessment |
| Features | Finance Agent + calculation tool library (versioned formulas); Market Agent + web search tool (first external-egress tool, exercising [11-security-architecture.md](11-security-architecture.md)'s egress logging) — **shipping with mandatory query sanitization and network-policy egress enforcement built in, per ACCB Mandatory Change 1 ([06-tool-architecture.md](06-tool-architecture.md) §6.6), and market-data caching routed through the knowledge-approval gate per ACCB Mandatory Change 2 ([09-knowledge-architecture.md](09-knowledge-architecture.md) §9.7) — neither is a follow-on hardening task for this milestone, both are launch preconditions for the Market Agent existing at all**; Risk Agent synthesizing Compliance+Finance+Market |
| Dependencies | Milestones 1–2 |
| Deliverables | Given an application's documents, the system produces a financial analysis and a risk rating, both fully cited |
| Risks | Market Agent egress control is a new trust boundary — requires its own focused security review before enabling in staging with real queries (R-S1); calculation-formula versioning discipline must be established now, since retrofitting it after formulas are in use is costlier |
| Acceptance criteria | Financial figures reconcile with manual verification; risk rating correctly reflects a documented conflicting-input test case (e.g., strong financials + hard compliance flag) by escalating rather than auto-resolving; **AND** a red-team test confirms a query containing simulated applicant PII is sanitized or rejected before any outbound call, and a simulated low-quality cached market finding is correctly held in the low-trust tier rather than reaching Risk/Recommendation as approved knowledge |
| Complexity | High |

## 14.6 Milestone 4 — Full Loan Assessment workflow

| | |
|---|---|
| Objective | Wire the Planner, `supervisor_service`, Recommendation Agent, and `publishing_service` into the complete Loan Assessment workflow template (Phase 7) |
| Features | Planner (bounded template selection, per [05-agent-architecture.md](05-agent-architecture.md) §5.2.1 — not task-graph generation); `services/supervisor_service` (dispatch/retry/escalation control logic); Recommendation Agent; `services/publishing_service` + Word/PDF/PowerPoint generation tools (merged Report+Presentation, per §5.11.1); full multi-day-pause approval gate exercised |
| Dependencies | Milestones 1–3 (assembles their agents and services into one workflow) |
| Deliverables | An officer can run a real application end-to-end: intake → parallel analysis → risk → recommendation → officer approval → committee report + deck, with a multi-day approval pause surviving a service restart |
| Risks | This is the highest-integration-complexity milestone — workflow-template dependency ordering (Phase 7) bugs are likeliest here (R-T2); officer trust/adoption risk becomes measurable for the first time (R-B1) |
| Acceptance criteria | End-to-end Loan Assessment completes with every [01-vision.md](01-vision.md) success criterion met on a pilot batch of real (or realistic de-identified) applications; workflow correctly resumes after a deliberate mid-approval restart drill |
| Complexity | High |

## 14.7 Milestone 5 — Voice and audit completeness

| | |
|---|---|
| Objective | Add the remaining two services and close the audit-completeness loop |
| Features | `services/voice_service` (TTS briefings, STT dictation — tool wrapping, not an agent, per §5.11.2); `services/audit_service` (structured query API plus its thin narrative-summarization layer, per §5.11.3); PDPA subject-access-request path exercised end-to-end |
| Dependencies | Milestone 4 (Voice Service narrates already-approved reports; Audit Service reconstructs already-running workflows) |
| Deliverables | Officers can request an audio briefing of an approved report and dictate notes; an Auditor can request and receive a complete reconstruction of any workflow instance |
| Risks | STT accuracy on Malay/English code-switched dictation (R-A3) |
| Acceptance criteria | Audit Service reconstruction matches ground truth on a test workflow with deliberately seeded gaps (confirms gaps are reported, not smoothed over, per [05-agent-architecture.md](05-agent-architecture.md) §5.11.3) |
| Complexity | Medium |

## 14.8 Milestone 6 — Production hardening and launch gate

| | |
|---|---|
| Objective | Close the gap between "works in staging" and "cleared for real applicant data in production" |
| Features | Full HA/DR implementation (Phase 13); third-party security assessment including prompt-injection red-teaming (Phase 11); load testing to target throughput; runbook completion (Phase 12) |
| Dependencies | Milestones 0–5 |
| Deliverables | Signed-off security assessment; DR drill completed; production go-live |
| Risks | Security assessment surfacing findings that require rework (R-S2 — budgeted for explicitly rather than treated as schedule risk) |
| Acceptance criteria | Security assessment passed with no unresolved critical/high findings; DR drill meets the RTO/RPO targets in [13-deployment-architecture.md](13-deployment-architecture.md) |
| Complexity | High (breadth, not novel logic) |

## 14.9 Milestone sequencing rationale

Milestones 1→3 deliberately build single-agent, single-workflow value before Milestone 4 attempts full multi-agent orchestration — this is what keeps Planner/`supervisor_service` integration risk isolated to one milestone instead of compounding with unproven individual agents. Voice and Audit services (Milestone 5) are sequenced after the core Loan Assessment workflow specifically because both depend on there being real completed workflow instances to narrate or reconstruct — building them earlier would mean testing against synthetic-only data. Production hardening is its own milestone, not folded into Milestone 4, because [01-vision.md](01-vision.md)'s data-sensitivity constraints mean "feature complete" and "cleared for real data" are genuinely different bars, and conflating them creates pressure to skip security review under feature-delivery deadline pressure.
