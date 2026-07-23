« [Index](00-INDEX.md) | Phase 1 of 16 »

# Phase 1 — Project Vision

## 1.1 Problem statement

MARA (Majlis Amanah Rakyat) officers at the Entrepreneurship Transformation Centre process high volumes of entrepreneur applications, loan/grant assessments, compliance checks, and committee reporting largely by hand: reading scanned documents, cross-checking figures against policy, drafting risk write-ups, assembling committee decks, and re-keying the same facts into multiple formats. The work is knowledge-heavy, repetitive in structure but high-stakes in content, and bottlenecked on officer time rather than on the availability of information.

A chatbot that answers questions does not fix this. The bottleneck is *task execution* — reading, extracting, cross-referencing, calculating, drafting, formatting — not *information retrieval* alone. MARA AI-ETC is therefore built as an agentic system: it plans work, executes it through tools, produces evidence-backed drafts, and hands off to a human for judgment and sign-off at defined checkpoints.

## 1.2 Goals

- **G1 — Reduce officer time-to-decision.** Compress the document-to-recommendation cycle (e.g., loan assessment intake to committee-ready report) from days to hours, without removing human judgment from the decision itself.
- **G2 — Standardize and evidence every output.** Every figure, claim, or recommendation the system produces is traceable to a source document, a calculation, or a policy citation — never an unsupported LLM assertion.
- **G3 — Build an AI workforce, not a single assistant.** Specialized agents (document extraction, compliance, finance, risk, market research, reporting, presentation, voice, audit) collaborate under a planner/supervisor, each auditable and independently improvable.
- **G4 — Keep humans as the decision authority.** Officers approve, correct, or reject at defined gates. The system never autonomously finalizes a loan decision, submits a compliance sign-off, or sends an external communication.
- **G5 — Produce enterprise-grade audit trails.** Every agent action, tool call, document access, and human approval/rejection is logged, attributable, and reconstructable for internal audit and PDPA accountability.
- **G6 — Ship on infrastructure MARA can operate and secure.** Self-hostable, data-residency-aware, and compatible with government security review processes — not a hard dependency on a single foreign SaaS vendor for data at rest.

## 1.3 Non-goals

- **Not a general-purpose public chatbot.** No open internet-facing conversational assistant; access is restricted to authenticated MARA officers and, in later phases, vetted applicants through narrow, tightly scoped interfaces (see [16-future-expansion.md](16-future-expansion.md)).
- **Not an autonomous approval system.** The system will never be the sole approver of a loan, grant, or compliance decision. Confidence scores and recommendations inform humans; they do not replace them.
- **Not a system-of-record replacement.** MARA AI-ETC orchestrates work and produces artifacts; it does not replace MARA's core loan/grant management systems or financial ledgers. It integrates with them (see integrations in [02-system-architecture.md](02-system-architecture.md)).
- **Not a real-time trading/decisioning system.** Workflows are measured in minutes to days, not milliseconds; we do not optimize for sub-second latency at the expense of auditability or correctness.
- **Not a from-scratch agent runtime.** We do not rebuild sandboxed execution, event streaming, or session management that OpenHands already provides — see the reuse matrix in [04-technology-stack.md](04-technology-stack.md).

## 1.4 Users

| User | Primary needs | Interaction mode |
|---|---|---|
| **Entrepreneurship Officers** | Fast, evidence-backed assessment drafts; ability to correct and approve | Workspace UI, day-to-day primary user |
| **Risk / Compliance Officers** | Policy-cross-checked flags, exception surfacing, audit-ready trails | Workspace UI + compliance dashboard |
| **Finance Officers** | Verified financial extraction and calculations from submitted documents | Workspace UI, finance review panel |
| **Committee Members / Approvers** | Concise, well-cited committee reports and decks; final decision authority | Report/presentation consumption, approval actions |
| **Branch / State Managers** | Portfolio-level visibility, throughput and risk dashboards | Dashboard, read-mostly |
| **System Administrators** | User/role management, agent and tool configuration, incident investigation | Admin console, observability stack |
| **Internal Auditors** | Full reconstructable history of decisions and system actions | Audit Service outputs, audit log viewer |

Entrepreneur/applicant-facing self-service is explicitly deferred — see [16-future-expansion.md](16-future-expansion.md) — because it introduces a materially different trust boundary (unauthenticated or lightly authenticated external users) that should not be solved in the same phase as internal officer tooling.

## 1.5 Business value

- **Throughput:** more applications assessed per officer-hour without proportionally growing headcount.
- **Consistency:** every assessment follows the same evidence-and-policy-citation standard, reducing variance between officers and between branches.
- **Auditability as a asset, not overhead:** a system built audit-first turns compliance reviews from a scramble into a query.
- **Institutional knowledge capture:** policy, precedent, and market data become a living, versioned knowledge base instead of tribal knowledge held by individual officers.
- **Faster committee cycles:** report and presentation generation collapse a multi-day drafting cycle into a same-day review cycle, increasing the number of committee sittings a portfolio can clear.

## 1.6 Success criteria

Success criteria are deliberately split into **adoption/quality** metrics (does it work and do officers trust it) and **efficiency** metrics (is it actually faster), because optimizing only for speed produces a system officers route around.

- ≥90% of extracted financial figures match manual verification on a sampled audit (accuracy of Document/Finance Agents).
- 100% of committee-report claims carry a source citation or explicit "unverified — officer input required" flag; zero silent unsupported claims.
- Median time from document intake to committee-ready draft reduced by a target percentage (baseline measured in Milestone 1, target set in Milestone 3 — see [14-roadmap.md](14-roadmap.md)) rather than pre-committed before a baseline exists.
- 100% of human approval/rejection/correction events recorded with actor, timestamp, and reason in the Audit Memory.
- Zero incidents of an agent taking an irreversible external action (submission, disbursement trigger, email to an applicant) without a passed human-approval gate.
- Officer-reported trust score (periodic survey) trending upward release over release, not just system-reported accuracy.

## 1.7 Constraints

- **Regulatory:** Malaysia's Personal Data Protection Act (PDPA) governs applicant personal and financial data; downstream government audit and procurement requirements likely apply (data residency, vendor risk assessment). Treated as a hard constraint on architecture, not an afterthought — see [11-security-architecture.md](11-security-architecture.md).
- **Data sensitivity:** entrepreneur financial statements, identity documents, and loan histories are sensitive by default; the system must support routing sensitive processing (OCR, LLM calls) to self-hosted or data-residency-compliant paths, not unconditionally to the cheapest cloud API.
- **Bilingual content:** source documents and officer workflows span Bahasa Malaysia and English, sometimes code-switched. OCR, LLM prompting, and generated documents must handle both.
- **Existing systems:** MARA already operates loan/grant systems of record; MARA AI-ETC must integrate with, not replace, them in this phase.
- **Operational capability:** the platform must be operable by MARA's own IT/security team over time, which argues against exotic, hard-to-hire-for infrastructure and for mainstream, well-documented open-source components (this directly shapes the stack choices in [04-technology-stack.md](04-technology-stack.md)).
- **Budget/complexity ceiling:** an enterprise agentic platform is a multi-quarter investment; the roadmap ([14-roadmap.md](14-roadmap.md)) is deliberately staged so that each milestone ships independently useful value rather than requiring the full system before anything is usable.
