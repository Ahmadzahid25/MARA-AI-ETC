« [Index](00-INDEX.md) | Phase 12 of 16 »

# Phase 12 — Observability

## 12.1 Why observability is distinct from audit

[08-memory-architecture.md](08-memory-architecture.md)'s Audit Memory answers "what happened, who decided, was it authorized" — a compliance/legal question, immutable and long-retained. Observability answers "is the system healthy, fast, and cost-effective, and why did this specific run behave the way it did" — an operational question, higher-volume, shorter-retained, and allowed to sample. Conflating them would either bloat the immutable audit store with high-cardinality debug data it doesn't need to retain forever, or under-instrument operations to keep the audit store lean. They share a correlation ID (the Gateway-issued request ID / LangGraph run ID, [02-system-architecture.md](02-system-architecture.md)) so an incident investigation can pivot between the two, but they are separate systems with separate retention policies.

## 12.2 Logging

Structured (JSON) logs from every service, agent runtime, and tool execution, shipped to Grafana Loki ([04-technology-stack.md](04-technology-stack.md)). Every log line carries: correlation ID, workflow ID, agent/service name, and severity. Tool-call logs additionally carry input/output hashes (not raw sensitive content, to keep operational logs out of PDPA scope — the actual content lives in Audit/Task Memory with its own access control, per [11-security-architecture.md](11-security-architecture.md)).

## 12.3 Tracing

OpenTelemetry spans across the full request path: Gateway → Planner/Supervisor → Workflow Engine node → Agent Runtime → Tool Runtime → external service, with the LangGraph run ID as the trace root. This is what makes "why did this Loan Assessment take 40 minutes instead of 5" answerable as a trace waterfall instead of log archaeology across six services.

## 12.4 Metrics

Prometheus-scraped metrics, Grafana-visualized, at minimum:
- **Per-agent**: invocation count, latency distribution, confidence-score distribution, escalation rate, tool-call count per invocation.
- **Per-tool**: invocation count, latency, error rate by error type, timeout rate.
- **Per-workflow**: instances started/completed/blocked, time-in-stage distribution (especially time-in-Approval, which is human-latency-dominated and a different signal from system latency), targeted-re-run rate from Validation failures.
- **Platform**: Gateway request rate/latency/error rate, queue depth (Redis/Celery), Postgres/pgvector query latency.

## 12.5 Agent Timeline

A per-workflow-instance view (in the Dashboard, [02-system-architecture.md](02-system-architecture.md)) rendering the full Start→Audit stage sequence from Phase 7 as a timeline: which agent ran when, its input/output summary, confidence score, and any escalation — built from the same trace/Task Memory data, not a separately maintained view, so it can never drift out of sync with what actually happened.

## 12.6 Tool Timeline

The tool-level equivalent, nested under each agent's timeline entry: every tool call an agent made, in order, with latency and outcome — this is the view an engineer uses to answer "which specific tool call caused this agent to escalate," distinct from the Agent Timeline's coarser per-agent granularity.

## 12.7 Cost tracking

Every LLM call and paid external API call (search, cloud OCR/TTS opt-in) is recorded with token counts/units and computed cost, attributed to workflow instance, agent, and initiating officer/branch — surfaced on the Dashboard as cost-per-workflow-type and cost-per-branch. This is what lets [14-roadmap.md](14-roadmap.md)'s efficiency claims be checked against actual operating cost, not just latency, and is also the first signal for the confidence-threshold tuning discussed in [10-human-in-the-loop.md](10-human-in-the-loop.md) (an agent with a high escalation rate is both a UX cost and an LLM-cost signal worth investigating together).

## 12.8 LLM usage

Langfuse ([04-technology-stack.md](04-technology-stack.md)) specifically tracks prompt/response pairs, prompt version in use, and per-agent model selection — this is the tool used when tuning an agent's prompt or evaluating a model swap, distinct from Prometheus/Grafana's operational-health view. Prompt versions are linked to `tests/agent_evals/` results (Phase 3), so a prompt change's effect on eval accuracy is visible before it's rolled out broadly.

## 12.9 Performance monitoring

SLOs are defined per layer, not just end-to-end, since end-to-end latency is dominated by human approval time and would mask a real regression elsewhere: Gateway p99 latency, Tool Runtime p99 latency by tool, Agent Runtime p99 latency by agent, Workflow Engine checkpoint-write latency. Alerting fires on SLO burn rate (standard multi-window burn-rate alerting), not on single-sample threshold breaches, to avoid alert fatigue from expected variance in LLM call latency.

## 12.10 Incident investigation

Standard path for "something went wrong": correlation ID (from a Dashboard-reported error or officer ticket) → OpenTelemetry trace for the exact call path and timing → Loki logs filtered to that correlation ID for detailed context → Langfuse for the specific LLM prompt/response if the issue is reasoning-related → Audit Memory (via the Audit Service) for the authoritative record of what was actually approved/rejected if the issue has any decision-integrity dimension. This ordered path is documented as a runbook in `docs/deployment/` ([03-repository-structure.md](03-repository-structure.md)) so incident response doesn't depend on institutional memory of which of the five systems to check first.

## 12.11 Retention

Observability data (logs, traces, metrics) is retained on an operational schedule (e.g., 30–90 days hot, longer cold-archived if storage-cost-justified) — explicitly shorter and more flexible than Audit Memory's regulatory retention, because it is a debugging aid, not a compliance record. This distinction is what keeps observability infrastructure sized for its actual purpose instead of growing unbounded under audit-grade retention requirements it doesn't need.
