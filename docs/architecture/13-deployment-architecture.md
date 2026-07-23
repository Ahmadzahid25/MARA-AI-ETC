« [Index](00-INDEX.md) | Phase 13 of 16 »

# Phase 13 — Deployment Architecture

## 13.1 Environments

| Environment | Purpose | Data | Deployment trigger |
|---|---|---|---|
| **Development** | Local iteration, `docker-compose` overlay ([03-repository-structure.md](03-repository-structure.md) `infrastructure/compose/`) | Synthetic/fixture data only, never real applicant data | Manual, per-developer |
| **Testing** | CI-run automated tests (unit, integration, `agent_evals`) | Synthetic fixtures + golden-document eval sets | Every PR, via GitHub Actions |
| **Staging** | Pre-production validation, mirrors production topology at reduced scale | De-identified/synthetic data resembling production shape; real data only under an explicit, logged, time-boxed exception for final UAT | Merge to main, via ArgoCD |
| **Production** | Live officer use | Real applicant/officer data, full security posture from [11-security-architecture.md](11-security-architecture.md) | Manual promotion from staging, via ArgoCD, requiring sign-off |

Staging never receives real applicant data by default because a lower-security-scrutiny environment holding real PDPA-covered data would undermine the entire data-residency/classification design in [11-security-architecture.md](11-security-architecture.md) — this is a rule enforced by data-seeding tooling in `scripts/`, not just policy.

## 13.2 High availability

- **Stateless services** (`services/*`, Tool Runtime, Agent Runtime): horizontally scaled behind the Gateway, no session affinity required since workflow state lives in Postgres (LangGraph checkpoints), not in-process — any worker can pick up any workflow's next step.
- **Postgres**: primary + read replica(s), with the primary as the single write target for checkpoint/audit consistency; managed-Postgres or a self-managed HA setup (e.g., Patroni) depending on final hosting decision.
- **Redis**: sentinel/cluster mode for the auxiliary queue, sized for graceful degradation — a Redis outage delays ancillary async jobs (email dispatch, audio rendering) without corrupting or losing core workflow state, because that state doesn't live in Redis.
- **Object storage**: MinIO in distributed mode (erasure-coded) for self-hosted deployments, or S3's native durability if cloud-hosted.
- **Approval Service** specifically is called out for aggressive HA (multiple replicas, fast failover) because, per [07-workflow-architecture.md](07-workflow-architecture.md)/[10-human-in-the-loop.md](10-human-in-the-loop.md), it is the single unblock path for every paused workflow — an outage here doesn't lose data (checkpoints persist) but does stall all in-flight human decisions system-wide.

## 13.3 Horizontal scaling

Kubernetes HPA (Horizontal Pod Autoscaler) on the stateless services, scaled on a blend of CPU/memory and queue-depth/request-latency signals rather than CPU alone, since LLM-bound agent workloads are I/O-wait-heavy (waiting on LLM API responses) and would under-scale on a CPU-only signal. The Tool Runtime's sandboxed execution pool is scaled separately from the Agent Runtime, since document-processing tools (OCR) and LLM-call-bound agent loops have different resource profiles and shouldn't compete for the same pod budget.

## 13.4 Disaster recovery

| Component | RPO | RTO | Strategy |
|---|---|---|---|
| Postgres (checkpoints, audit, memory) | ≤ 5 min | ≤ 1 hr | Continuous WAL archiving + point-in-time recovery; cross-region/cross-site replica for the DR site |
| Object storage (documents, artifacts) | ≤ 15 min | ≤ 1 hr | Versioned bucket replication to a secondary site |
| Configuration/secrets | 0 (git-tracked / Vault-replicated) | ≤ 30 min | GitOps (ArgoCD) means environment state is reconstructable from git; Vault replication for secrets |
| Full platform | — | ≤ 4 hr | Documented, periodically drilled runbook (`docs/deployment/`) to stand up the full stack from backups + GitOps manifests in the DR site |

Audit Memory's RPO is treated as the tightest requirement in the system (effectively zero tolerance for silent loss) given its role as the accountability record ([08-memory-architecture.md](08-memory-architecture.md), [11-security-architecture.md](11-security-architecture.md)) — WAL archiving is configured with this specifically in mind, not just general database hygiene.

## 13.5 Backups

- Postgres: nightly full + continuous WAL, tested restore drills on a defined cadence (not just backup-exists checks — an untested backup is not a verified backup).
- Object storage: versioning enabled, lifecycle policy balancing retention requirements (Phase 8/11) against storage cost for superseded artifact versions.
- Backup encryption and access control mirror production data controls — a backup is a copy of the same sensitive data and is not exempt from [11-security-architecture.md](11-security-architecture.md).

## 13.6 Container strategy

One container image per `services/*` boundary and per major tool category ([03-repository-structure.md](03-repository-structure.md)), built via the existing OpenHands `containers/` conventions and Makefile targets, extended rather than replaced. The Tool Runtime's sandbox containers are rebuilt/scanned on a security-patch cadence independent of application releases, since they execute untrusted document content and are the highest-exposure surface in the system.

## 13.7 Kubernetes readiness

The existing `kind/` directory (local Kubernetes via kind, already in the OpenHands checkout) is the starting point for local K8s validation before staging; production manifests/Helm charts live in `infrastructure/k8s/`. Namespacing separates by trust boundary, not just by team convenience: sandboxed Tool Runtime workloads run in a distinct, more tightly network-policed namespace from the Gateway/API services, consistent with [11-security-architecture.md](11-security-architecture.md)'s least-privilege network posture.

## 13.8 Cloud readiness

Designed cloud-agnostic-by-default (Postgres, MinIO/S3-compatible storage, Redis, Kubernetes all have equivalent managed offerings across major providers and equivalent self-hosted forms) so the same manifests target either a MARA-operated on-prem/government-cloud environment or a commercial cloud, decided on data-residency and procurement grounds ([01-vision.md](01-vision.md) constraints) rather than architecture constraints. Terraform modules in `infrastructure/terraform/` are written per-provider behind a common interface (network, managed DB, object storage, K8s cluster) so a provider change is a module swap, not a redesign.
