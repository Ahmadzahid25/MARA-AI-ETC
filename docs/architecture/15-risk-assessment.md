« [Index](00-INDEX.md) | Phase 15 of 16 »

# Phase 15 — Risk Assessment

Risk IDs referenced from [14-roadmap.md](14-roadmap.md) are cross-linked below so a milestone's flagged risk has a concrete mitigation owner and plan, not just a name.

## 15.1 Technical risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-T1 | Forking OpenHands' `app_server` for MARA-specific permission/tool constraints takes materially longer than estimated, or fights the upstream architecture in ways that weren't visible from folder-structure inspection alone | Medium | Medium | Milestone 0 is scoped specifically to surface this early, before any agent depends on the fork being stable; a technical spike against `app_server/event` and `sandbox` internals is the first task, not an assumed-solved prerequisite |
| R-T2 | Task-graph dependency ordering (Planner/Supervisor, Phase 7) has subtle bugs under partial-failure conditions (e.g., a targeted re-run interacting badly with already-published Shared Memory) | Medium | High | Milestone 4 includes deliberate chaos-style testing (kill a worker mid-workflow, force a Validation failure) before the milestone is considered complete, not just happy-path testing |
| R-T3 | LangGraph checkpoint schema evolves between platform versions in a way that breaks resuming an in-flight, multi-day-paused workflow | Low-Medium | High (a stuck loan application is a real officer/applicant impact) | Explicit schema-versioning policy on checkpoint state (Phase 6.4); staging always tests a checkpoint-resume-across-deploy scenario before a production deploy that touches workflow state shape |
| R-T4 | Dify-as-a-service integration point becomes a bottleneck or single point of failure for all RAG-dependent agents | Medium | Medium | Isolation via `services/knowledge_service` (Phase 9.8) means a Dify replacement is a contained change; HA configuration for the Knowledge Service is explicit in Phase 13, not assumed |

## 15.2 Business risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-B1 | Officer adoption is low because the system is perceived as adding review overhead rather than saving time (a real risk any human-in-the-loop system faces) | Medium | High | Success criteria in [01-vision.md](01-vision.md) explicitly include officer-reported trust, not just system-reported speed; Milestone 4 is the first point this is measurable, and roadmap sequencing keeps early milestones narrow enough to gather this feedback before over-investing in scope officers don't want |
| R-B2 | Scope creep toward "autonomous decisioning" under throughput pressure, eroding the human-approval principle that is this system's core trust proposition | Low-Medium | Very High | The always-required approval gates (Phase 10.3) are structurally enforced, not configurable away — this is a governance control against the business risk, not just a UX choice |
| R-B3 | Committee/officer resistance to citation-heavy outputs perceived as verbose compared to current free-form reports | Medium | Low-Medium | Publishing service templates (Phase 5.11.1) are iterated with actual committee feedback starting in Milestone 4's pilot, not finalized upfront |

## 15.3 Security risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-S1 | Market Agent's web-search egress becomes a data-exfiltration path (accidental or adversarial) since it's the system's only outbound-internet tool | Low-Medium | High | Milestone 3 explicitly gates this tool's staging rollout on a focused security review (Phase 14.5); egress logging (Phase 11.7) and domain allow-listing are enforced at the Tool Runtime, not agent-trusted |
| R-S2 | Third-party security assessment (Milestone 6) surfaces findings requiring architectural rework, not just patches | Medium | Medium (budgeted, not schedule-fatal) | Roadmap explicitly separates "feature complete" from "cleared for production" (Phase 14.9) so this risk lands as planned rework time, not a surprise |
| R-S3 | Prompt injection via a malicious or adversarially-crafted uploaded document causes an agent to attempt out-of-scope actions | Medium | High | Defense-in-depth tool permission enforcement independent of LLM behavior (Phase 11.6) means even a successful injection has no path to an unauthorized effect; red-teaming this specifically is a named Milestone 6 activity |
| R-S4 | A compromised or misconfigured component suppresses its own audit trail | Low | Very High | Audit Memory is written independently by three separate components (Supervisor, Tool Runtime, Approval Service — Phase 8.2), so no single compromise silences the record |

## 15.4 Operational risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-O1 | MARA's IT team lacks in-house Kubernetes/LangGraph/Postgres-at-scale operational experience, creating a bus-factor and incident-response risk post-launch | Medium | High | Stack choices in Phase 4 deliberately favor mainstream, well-documented, widely-hired-for technology over exotic alternatives for exactly this reason; runbooks (Phase 12.10, 13) are a Milestone 6 deliverable, not an afterthought |
| R-O2 | Approval Service outage stalls every in-flight workflow system-wide (Phase 13.2 names this explicitly) | Low | High | Aggressive HA configuration specifically for this service; checkpoints mean an outage delays but does not lose or corrupt state |
| R-O3 | Blocked-workflow accumulation (Phase 7.5) goes unmonitored, silently growing a backlog of stuck applications | Medium | Medium | Dashboard surfaces blocked-workflow count/age explicitly (Phase 2.2); alerting on blocked-workflow age is part of the Phase 12 SLO set |

## 15.5 AI-specific risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-A1 | OCR accuracy on real MARA document formats (varied scan quality, handwriting, bilingual mixed-language forms) is materially below the assumed baseline | Medium-High | Medium | Named explicitly as Milestone 1's core risk (Phase 14.3) — proven early on the simplest agent before three more agents build on the assumption that extraction is reliable |
| R-A2 | Policy corpus is incomplete or inconsistently structured, causing the Compliance Agent to report "no applicable policy found" far more often than useful, undermining trust in the whole compliance-check feature | Medium | Medium | Milestone 2 treats this as an expected finding to plan around, not a failure mode — a high "no policy found" rate is itself a signal fed back to Knowledge Owners (Phase 9.6) to prioritize corpus gaps |
| R-A3 | STT accuracy on Malay/English code-switched speech is materially lower than on monolingual audio, given Whisper's uneven code-switching performance | Medium | Low-Medium (Voice Service is not on the critical decision path) | Confidence threshold (0.85, Phase 5.11.2) blocks low-confidence transcripts from being treated as authoritative without officer confirmation; Voice Service is scoped after core workflow (Milestone 5) precisely so this risk doesn't block higher-value work |
| R-A4 | LLM hallucination/unsupported-claim generation slips through despite the provenance-block requirement, because prompt-level instruction alone is an imperfect control | Medium | High | Provenance is enforced at the output-schema level (Phase 5.1), not prompt instruction alone — a response missing required citation fields fails schema validation before it reaches a human, and `tests/agent_evals/` regression-tests specifically for unsupported-claim cases |
| R-A5 | Confidence scores are poorly calibrated (an agent's stated 0.9 confidence doesn't actually correspond to 90% correctness), undermining the entire escalation-threshold mechanism | Medium | High | Long-term Memory's calibration tracking (Phase 8.2) and correction-feedback loop (Phase 10.5) exist specifically to detect and correct this over time; thresholds are reviewed against actual correction rates, not set once and forgotten |

## 15.6 Scaling risks

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-SC1 | LLM API cost scales faster than officer-hour savings as adoption grows, undermining the business case | Medium | Medium | Cost tracking (Phase 12.7) is per-workflow and per-branch from day one, not added after cost becomes a problem; self-hosted model fallback (Phase 4.6) is a deliberate cost/data-residency lever, not just a security one |
| R-SC2 | Knowledge Base retrieval latency/quality degrades as the corpus grows well beyond initial pilot scale | Low-Medium (mitigated path exists) | Medium | pgvector-to-Qdrant migration path (Phase 4.3) is pre-planned, not a redesign-on-demand |
| R-SC3 | Tool Runtime sandbox pool becomes a throughput bottleneck as concurrent workflow volume grows (e.g., OCR-heavy batch periods) | Medium | Medium | Scaled independently from the Agent Runtime (Phase 13.3) specifically so this doesn't require over-provisioning the whole platform to fix one hot path |
| R-SC4 | Cross-department/system expansion (Phase 16) is attempted before the core platform's multi-tenancy and permission model have been proven at single-department scale | Low (roadmap-controlled) | Medium | Explicitly sequenced after Milestone 6 in [16-future-expansion.md](16-future-expansion.md), not a parallel track |

## 15.7 Risk review cadence

This register is a living document, reviewed at each milestone boundary in [14-roadmap.md](14-roadmap.md) — likelihood/impact ratings here are pre-implementation estimates and are expected to be revised once each milestone produces real evidence (e.g., R-A1's actual OCR accuracy, once measured in Milestone 1, replaces the estimate above).
