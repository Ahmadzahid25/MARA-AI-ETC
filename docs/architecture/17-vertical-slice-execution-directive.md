# Phase 17 - Vertical Slice Execution Directive

Status: active directive
Effective date: 2026-07-29
Scope: replaces implementation priority in Phase 14 until the first end-to-end grant workflow demo is running.

This document is an execution directive, not a new target architecture. The 16-phase baseline remains valid as the long-term design. This directive changes delivery order so the team ships a running workflow first, then continues staged hardening.

## 17.1 Why this directive exists

The current program has strong domain agents, tools, workflows, and contracts, but no fully verified end-to-end execution in a real running environment. The highest risk is delivery drift: planning and refactoring continue while the core grant flow is still not demonstrably running.

This directive creates one temporary rule:

1. No new architecture expansion work starts until the first vertical slice passes the smoke-test definition in 17.4.

## 17.2 Boundaries

In scope now:

1. Applicant intake to officer decision, with audit trail.
2. Minimal infrastructure needed to run and verify the flow.
3. Stabilization fixes required to keep the flow running.

Out of scope until 17.4 passes:

1. Additional phase expansions (voice, advanced market integrations, extra dashboards).
2. Broad repo-wide refactors not required by the vertical slice.
3. New architecture documents beyond one execution status update file if needed.

## 17.3 Delivery sequence (mandatory)

### R0 - Stabilize and trim for execution

1. Fix known documentation drift in top-level status messaging.
2. Resolve workflow policy ambiguity for acknowledged hard compliance violations.
3. Freeze scope to the vertical slice below.

### R1 - Data and auth foundations

1. Define and migrate core models:
	- applicants
	- businesses
	- applications
	- documents
	- audit_log
2. Implement role-aware auth for three roles:
	- applicant
	- officer
	- admin

### R2 - Applicant portal path

1. Register/login.
2. Submit application form.
3. Upload required documents.
4. View application status timeline.

### R3 - Workflow wiring

1. Trigger loan_assessment asynchronously after submit.
2. Persist workflow state durably.
3. Pause at recommendation_approval gate.
4. Resume from officer decision.

### R4 - Officer workspace path

1. Application queue view.
2. Case detail view with extraction and analysis outputs.
3. Decision actions:
	- approve
	- reject
	- request_more_info

### R5 - End-to-end demo stabilization

1. Run smoke test end-to-end repeatedly.
2. Fix failures until stable.
3. Record evidence in tests and logs.

## 17.4 Vertical slice done definition (must pass)

The following seven steps must run in one environment with reproducible results:

1. Applicant registers/logs in, submits a grant application, and uploads at least three files (IC, bank statement PDF, SSM certificate).
2. Backend stores the application with SUBMITTED state and triggers loan_assessment.
3. Document path produces classification, extraction, and completeness output.
4. Finance, risk, and recommendation outputs are generated for the same application.
5. Workflow pauses at recommendation_approval using durable interrupt/resume behavior.
6. Officer reviews the case and executes approve/reject/request_more_info.
7. Applicant status updates and audit_log receives immutable action entries for both agent and officer actions.

Until all seven steps pass, other architecture-phase expansion work remains parked.

## 17.5 Temporary simplifications allowed

To reduce time to first running slice, these simplifications are allowed temporarily:

1. Non-critical approval gates may be stubbed as auto-pass.
2. Non-critical integrations may run with local or mocked adapters.
3. Observability may start with structured stdout logging.

Any simplification must:

1. Be explicit in code comments and tests.
2. Have a named follow-up issue.
3. Preserve auditability and human final decision control.

## 17.6 Guardrails (cannot be relaxed)

1. Human officer is final decision authority.
2. Audit log is insert-only and attributable.
3. Evidence/citation fields must not be silently fabricated.
4. Sensitive data handling must follow existing PDPA controls.

## 17.7 Exit criteria and handback to Phase 14

This directive expires when:

1. 17.4 passes in a repeatable run.
2. Smoke test is automated.
3. The team records closure in Phase 14 with the next milestone state.

After expiry, normal roadmap sequencing in Phase 14 resumes.

## 17.8 Parallel execution matrix (start immediately)

Run four lanes in parallel. Each lane has strict boundaries and a handoff artifact so work is not duplicated.

### Lane A - Backend core (lead)

Scope:

1. Core models and migrations for applicants/businesses/applications/documents/audit_log.
2. Auth and role enforcement for applicant/officer/admin.
3. API endpoints for submit, status, officer review decisions.

Handoff artifacts:

1. OpenAPI snapshot for frontend consumption.
2. Seed script and example payloads.
3. One integration test per endpoint family.

### Lane B - Workflow integration (lead)

Scope:

1. Trigger `loan_assessment` on submit.
2. Persist/reload workflow state.
3. Pause/resume at `recommendation_approval`.

Handoff artifacts:

1. Workflow runbook for local demo.
2. Contract for `ai_assessment` payload shape persisted to `applications`.
3. Resume API contract used by officer actions.

### Lane C - Applicant web path (frontend)

Scope:

1. Register/login.
2. Multi-step application form.
3. Document upload and status tracker.

Handoff artifacts:

1. Frontend field map against backend schema.
2. Error-state matrix (validation, upload, auth expiry).
3. Smoke-test script for applicant path.

### Lane D - Officer review path (frontend)

Scope:

1. Queue list.
2. Case detail with extraction/analysis/recommendation.
3. Approve/reject/request_more_info actions.

Handoff artifacts:

1. Review page contract checklist against API response.
2. Action-to-status transition table.
3. Smoke-test script for officer path.

## 17.9 Anti-rework protocol (mandatory)

1. Contract-first: backend publishes schema and endpoint examples before frontend wiring starts for that feature.
2. No silent contract changes: any request/response change updates both AGENTS briefs and test fixtures in the same PR.
3. One owner per artifact: models, API contract, and UI mapping each have a single owner per sprint.
4. Feature flags for incomplete gates: unfinished gates stay explicit behind flags or auto-pass stubs, never half-enabled.
5. Daily dependency cut: each lane declares blockers and handoffs at day end; no lane starts speculative work without the dependent artifact.
6. Merge by vertical behavior: PRs are accepted when an end-user behavior moves forward, not when internal refactor volume is high.

## 17.10 First 10-day execution window

Day 1-2:

1. Freeze payload contracts and role model.
2. Finalize migration skeleton.
3. Define smoke-test scenario data.

Day 3-5:

1. Ship submit/status APIs and applicant form wiring.
2. Wire workflow trigger and persistence.
3. Expose officer queue/read endpoints.

Day 6-8:

1. Ship officer decision actions and resume path.
2. Complete applicant status updates from workflow events.
3. Add audit-log writes for all critical actions.

Day 9-10:

1. Run full smoke test repeatedly.
2. Fix blocking defects only.
3. Record closure evidence for 17.4 steps.

## 17.11 Contract freeze v1 (single source)

This section is the frozen v1 contract for the first vertical slice. Frontend and backend must implement these shapes before adding optional fields.

### Core state enums

`applications.status`:

1. `DRAFT`
2. `SUBMITTED`
3. `PROCESSING`
4. `NEEDS_INFO`
5. `UNDER_REVIEW`
6. `APPROVED`
7. `REJECTED`

Officer decision action:

1. `approve`
2. `reject`
3. `request_more_info`

### Minimal API table (v1)

1. `POST /api/v1/auth/register`
Purpose: applicant account creation.
Request: `{ full_name, email, password }`.
Response: `{ user_id, role, access_token }`.

2. `POST /api/v1/auth/login`
Purpose: role-aware login (applicant/officer/admin).
Request: `{ email, password }`.
Response: `{ user_id, role, access_token }`.

3. `POST /api/v1/applications`
Purpose: create and submit application.
Request: `{ applicant, business, financing, documents[] }`.
Response: `{ application_id, status }` where initial status is `SUBMITTED`.

4. `GET /api/v1/applications/{application_id}`
Purpose: applicant/officer detail view.
Response: `{ application_id, status, applicant, business, financing, ai_assessment, workflow }`.

5. `POST /api/v1/applications/{application_id}/documents`
Purpose: upload supporting document after application creation.
Request: multipart form with `file` and `doc_type`.
Response: `{ application_id, document }`.

6. `GET /api/v1/applications/{application_id}/status`
Purpose: status timeline.
Response: `{ application_id, status, stage_log[], updated_at }`.

7. `GET /api/v1/officer/applications`
Purpose: officer queue.
Response: `{ items: [{ application_id, applicant_name, scheme, amount_requested, status, updated_at }] }`.

8. `POST /api/v1/officer/applications/{application_id}/decision`
Purpose: officer gate decision and workflow resume.
Request: `{ action, reason, conditions? }` where `action` is one of `approve|reject|request_more_info`.
Response: `{ application_id, status, decision_recorded_at }`.

### `ai_assessment` minimal persisted shape

`applications.ai_assessment` (JSON object) must contain:

1. `extraction_summary`.
2. `compliance_summary`.
3. `financial_summary`.
4. `risk_summary`.
5. `recommendation` object with:
	- `decision` (nullable)
	- `withheld_reason` (nullable)
	- `confidence`
	- `has_acknowledged_violation` (boolean)
6. `citations` array.
7. `stage_log` array.

## 17.12 Daily smoke-test checklist (R5 and onward)

Run this checklist at least once per day and on every integration PR:

1. Applicant register/login succeeds.
2. Applicant creates and submits one application with three documents.
3. Application status transitions `SUBMITTED` -> `PROCESSING`.
4. Workflow writes extraction/compliance/finance/risk/recommendation into `ai_assessment`.
5. Workflow pauses at `recommendation_approval`.
6. Officer queue shows the application.
7. Officer opens detail and sees recommendation payload including `has_acknowledged_violation`.
8. Officer action `approve` resumes workflow and updates status.
9. Officer action `request_more_info` updates status to `NEEDS_INFO`.
10. Audit log has entries for agent actions and officer decision actions (insert-only behavior).

A smoke run is considered pass only when all 10 checks pass in one environment run.
