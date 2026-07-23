« [Index](00-INDEX.md) | Phase 16 of 16 »

# Phase 16 — Future Expansion

Everything in this phase is explicitly **post-Milestone 6** ([14-roadmap.md](14-roadmap.md)) — none of it is a prerequisite for, or should be allowed to dilute focus from, the core officer-facing platform reaching production. Each item below states what in the existing architecture already makes it feasible, so expansion is additive, not a redesign.

## 16.1 Voice-first workflow

The Voice Service (Phase 5.11.2) already exists as TTS/STT at the artifact level (briefings, dictation). Voice-first expansion means making voice a primary interaction mode for a full workflow (e.g., an officer verbally walking through a Loan Assessment review) rather than an output format. Feasible because the Agent Runtime's event-stream model (Phase 4.1) is already modality-agnostic — a voice turn is just another event type, not a parallel system. Requires: real-time STT streaming (vs. the current batch-file model), and UX research into whether voice interaction actually suits the compliance-sensitive review task, given [11-security-architecture.md](11-security-architecture.md)'s concern about STT confidence and authoritative input.

## 16.2 Mobile workspace

The API Gateway (Phase 2.2) is already the single entry point for all clients, so a mobile client is an additional frontend consuming the same Gateway contract — not a backend change. Scope would likely start read-mostly (Dashboard, pending-approval notifications, quick approve/reject) before attempting full document review on a small screen, since the Review & Approval Console's evidence-presentation requirement (Phase 10.4) is genuinely harder to satisfy well on mobile.

## 16.3 Additional MARA systems

Integration with MARA's other systems of record (beyond loan/grant, e.g., training program management, entrepreneur portfolio tracking) follows the same Integrations-layer pattern already established (Phase 2.2, 6.2) — new integrations are added as tools with the same permission/audit discipline as existing ones, not a special-cased bypass. Prioritization should follow the same "prove one, then extend" discipline as [14-roadmap.md](14-roadmap.md) — one additional system integrated and validated before a second is attempted in parallel.

## 16.4 MCP servers

The Tool Runtime's MCP host (`app_server/mcp`, Phase 4.1/6.5) is already the designated extension point for new tools. Future expansion here means MARA (or partner agencies) exposing their own capabilities as MCP servers that MARA AI-ETC's agents can call — e.g., a national business-registry lookup service, or another agency's compliance-check API — without any change to the core platform. This is architecturally the cheapest expansion path in this phase precisely because it was designed in from Phase 6, not bolted on.

## 16.5 Government integrations

Broader integration with national identity verification (e.g., MyDigital ID-style federated identity), inter-agency data-sharing APIs, or national credit bureau data. These carry materially higher security/legal scrutiny than internal MARA integrations and should each go through the same security-assessment gate as Milestone 6 (Phase 14.8), not a lighter-weight process just because the integration itself is small in code terms — the data-sensitivity and legal-agreement work dominates the effort, not the API integration.

## 16.6 Analytics

Beyond the operational Dashboard (Phase 2.2, 12), a dedicated analytics layer — trend analysis across a portfolio (sector risk trends, approval-rate patterns by branch, agent accuracy trends over time) — becomes viable once enough completed, audited workflow instances exist to analyze (a direct consumer of Audit/Task Memory, Phase 8). This is deliberately not built early: analytics on a small, pilot-scale dataset produces misleading patterns, and premature dashboard investment competes for the same engineering time Milestones 1–6 need.

## 16.7 Autonomous scheduling

Proactive, system-initiated work — e.g., the system noticing a policy update (Phase 9) and autonomously flagging every in-flight workflow that cited the superseded version, or scheduling periodic portfolio risk re-reviews — is a natural extension of the Workflow Engine (LangGraph can be triggered by events, not just officer-initiated requests) but must be designed carefully against the "human officers make the final decision" principle ([00-INDEX.md](00-INDEX.md)): autonomous *triggering* of a review workflow is acceptable; autonomous *completion* of one without human approval gates is not, and this phase's designs must not weaken that distinction just because the trigger became automated.

## 16.8 Cross-department collaboration

Multi-department workflows (e.g., a case requiring both Entrepreneurship and a separate Legal/Compliance department's sign-off) extend the existing RBAC/ABAC model (Phase 11.2) and the Approval Service's role-mapping (Phase 10.2) — both were designed to be configuration-driven specifically so a new approver role or department scope doesn't require an architectural change, only a configuration and workflow-graph update.

## 16.9 Entrepreneur/applicant-facing self-service

Explicitly named as a non-goal for the current scope ([01-vision.md](01-vision.md) 1.3) and repeated here because it's the most architecturally significant future expansion: it introduces external, less-trusted users into a system currently designed around authenticated internal officers. This is not a simple frontend addition — it requires revisiting the trust model in [11-security-architecture.md](11-security-architecture.md) (external user authentication, much stricter rate limiting and abuse protection, a narrower and more heavily sandboxed tool/agent surface exposed to that user class, and likely a separate Gateway deployment rather than the same one officers use). Should be scoped as its own architecture review when pursued, not assumed to be a UI-only extension of the officer workspace.

## 16.10 Sequencing principle for all of the above

None of Phase 16 is prioritized within this plan — that is intentionally a future decision informed by real Milestone 1–6 usage data (which agent has the highest officer-reported value, where the actual bottlenecks turn out to be) rather than speculation made before the core system has a single real user. The architecture is built to make each of these additive rather than requiring rework specifically so that decision can be deferred without technical debt accumulating while it's deferred.
