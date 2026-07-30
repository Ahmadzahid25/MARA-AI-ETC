import type { FieldCorrection } from '../types/approval';
import type { ChatMessage, Task } from '../types/workspace';
import type {
  DashboardStats,
  WorkflowInstance,
  AgentMetric,
  RiskFlag,
  PendingApprovalSummary,
} from '../types/dashboard';
import type { AdminUser, AdminRole, AgentProfile, SystemSetting } from '../types/admin';
import {
  createAssessment as apiCreateAssessment,
  submitDecision as apiSubmitDecision,
  ApiError,
  type AssessmentResponse,
  type CreateAssessmentInput,
  type DecisionInput,
  type V1OfficerQueueItem,
  type V1ApplicationStatus,
  type V1ApplicationDetailOutput,
  type V1ApplicationStatusOutput,
  type V1OfficerDecisionAction,
  listOfficerApplications,
  getApplicationDetail as apiGetApplicationDetail,
  getApplicationStatus as apiGetApplicationStatus,
  submitOfficerApplicationDecision as apiSubmitOfficerApplicationDecision,
  uploadApplicationDocument as apiUploadApplicationDocument,
} from './api';

let useMockMode = false;

export function setUseMock(useMock: boolean) {
  useMockMode = useMock;
}

export function getUseMock(): boolean {
  return useMockMode;
}

// ─── Empty fallbacks ─────────────────────────────────────────────────────────
// These are used ONLY when the real API is unreachable (network error / 5xx).
// They are deliberately empty so no fake data is ever shown to the user.
// All real data must come from the backend API.
const EMPTY_QUEUE_ITEMS: V1OfficerQueueItem[] = [];
const EMPTY_USERS: AdminUser[] = [];
const EMPTY_ROLES: AdminRole[] = [];
const EMPTY_AGENT_PROFILES: AgentProfile[] = [];
const EMPTY_SYSTEM_SETTINGS: SystemSetting[] = [];

function mapV1StatusToTaskStatus(status: V1ApplicationStatus): Task['status'] {
  if (status === 'PROCESSING') return 'in_progress';
  if (status === 'UNDER_REVIEW') return 'awaiting_approval';
  if (status === 'APPROVED') return 'completed';
  if (status === 'NEEDS_INFO') return 'blocked';
  if (status === 'REJECTED') return 'failed';
  return 'pending';
}

function queueItemToWorkflow(item: V1OfficerQueueItem): WorkflowInstance {
  return {
    id: item.application_id,
    title: `${item.scheme} - ${item.applicant_name}`,
    applicant: item.applicant_name,
    status: mapV1StatusToTaskStatus(item.status),
    stage: item.status.replace(/_/g, ' '),
    created_at: item.updated_at,
    updated_at: item.updated_at,
    assigned_agent: 'Loan Workflow',
    confidence: 0.92,
  };
}

export async function fetchOfficerQueueItems(): Promise<V1OfficerQueueItem[]> {
  if (useMockMode) {
    return EMPTY_QUEUE_ITEMS;
  }
  try {
    const queue = await listOfficerApplications();
    return queue.items ?? [];
  } catch (err) {
    console.warn('API /api/v1/officer/applications gagal:', err);
    return EMPTY_QUEUE_ITEMS;
  }
}

// ─── Dashboard ────────────────────────────────────────────────

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const items = await fetchOfficerQueueItems();
  const workflows = items.map(queueItemToWorkflow);

  const activeWorkflows = workflows.filter(
    (w) => w.status === 'in_progress' || w.status === 'awaiting_approval',
  ).length;
  const blockedWorkflows = workflows.filter((w) => w.status === 'blocked').length;
  const pendingApprovals = workflows.filter(
    (w) => w.status === 'awaiting_approval',
  ).length;

  return {
    total_workflows: workflows.length,
    active_workflows: activeWorkflows,
    pending_approval_count: pendingApprovals,
    blocked_workflows: blockedWorkflows,
    risk_flags_outstanding: blockedWorkflows,
  };
}

export async function fetchWorkflows(): Promise<WorkflowInstance[]> {
  const items = await fetchOfficerQueueItems();
  return items.map(queueItemToWorkflow);
}

export async function fetchAgentMetrics(): Promise<AgentMetric[]> {
  // TODO: wire to GET /api/v1/admin/agent-metrics when endpoint is ready
  return [];
}

export async function fetchRiskFlags(): Promise<RiskFlag[]> {
  const items = await fetchOfficerQueueItems();
  return items
    .filter((item) => item.status === 'NEEDS_INFO' || item.status === 'UNDER_REVIEW')
    .map((item) => ({
      id: `risk-${item.application_id}`,
      workflow_id: item.application_id,
      description: `${item.scheme}: Dokumen sokongan tambahan / maklumat risiko diperlukan.`,
      severity: item.amount_requested > 200000 ? 'high' : ('medium' as const),
      created_at: item.updated_at,
      agent_name: 'Risk Agent',
      status: 'open' as const,
    }));
}

export async function fetchPendingApprovals(): Promise<PendingApprovalSummary[]> {
  const items = await fetchOfficerQueueItems();
  const nowMs = Date.now();
  return items
    .filter((item) => item.status === 'UNDER_REVIEW')
    .map((item) => {
      const updatedMs = new Date(item.updated_at).getTime();
      const ageHours = Number.isNaN(updatedMs)
        ? 0
        : Math.max(0, (nowMs - updatedMs) / (1000 * 60 * 60));

      return {
        id: `approval-${item.application_id}`,
        workflow_title: `${item.scheme} - ${item.applicant_name}`,
        agent_name: 'Recommendation Agent',
        question: 'Adakah anda bersetuju dengan cadangan pembiayaan permohonan ini?',
        created_at: item.updated_at,
        age_hours: ageHours,
        status: 'pending' as const,
        assigned_to: 'Pegawai MARA',
      };
    });
}

// ─── Workspace ─────────────────────────────────────────────────

export async function fetchMessages(): Promise<ChatMessage[]> {
  return [];
}

export async function fetchTasks(): Promise<Task[]> {
  return [];
}

export async function startAssessment(
  input: CreateAssessmentInput,
): Promise<{ threadId: string; pendingGate: string | null }> {
  const res = await apiCreateAssessment(input);
  return { threadId: res.thread_id, pendingGate: res.pending_gate };
}

export async function startAssessmentFull(
  input: CreateAssessmentInput,
): Promise<AssessmentResponse> {
  return apiCreateAssessment(input);
}

// ─── Review Console & Officer Decision ────────────────────────────

export async function submitGateDecision(
  threadId: string,
  action: 'approve' | 'reject' | 'correct',
  reason?: string,
  corrections?: FieldCorrection[],
): Promise<AssessmentResponse> {
  const input: DecisionInput = { action, reason };
  if (corrections) input.corrections = corrections.map((c) => ({
    field_name: c.field_name,
    corrected_value: c.corrected_value,
    reason: c.reason,
  }));
  return apiSubmitDecision(threadId, input);
}

export async function submitOfficerDecision(
  applicationId: string,
  action: V1OfficerDecisionAction,
  reason?: string,
  conditions?: string[],
) {
  try {
    return await apiSubmitOfficerApplicationDecision(applicationId, {
      action,
      reason,
      conditions,
    });
  } catch (err) {
    throw err;
  }
}

export function extractGateRole(detail: string): string | null {
  const match = detail.match(/requires\s+(\w+(?:\s+\w+)*)/i);
  return match ? match[1] ?? null : null;
}

export { ApiError };

// ─── Admin Console ─────────────────────────────────────────────
// TODO: wire each function to real API endpoints when they are available.
// Until then, return empty lists so no fake data is shown.

export async function fetchUsers(): Promise<AdminUser[]> {
  return EMPTY_USERS;
}

export async function fetchRoles(): Promise<AdminRole[]> {
  return EMPTY_ROLES;
}

export async function fetchAgentProfiles(): Promise<AgentProfile[]> {
  return EMPTY_AGENT_PROFILES;
}

export async function fetchSystemSettings(): Promise<SystemSetting[]> {
  return EMPTY_SYSTEM_SETTINGS;
}

// ─── Detail Application Fetch (FE-P3) ─────────────────────────

export async function getApplicationDetailWithFallback(
  applicationId: string,
): Promise<V1ApplicationDetailOutput> {
  // Always fetch from the real API — no fake fallback data.
  return apiGetApplicationDetail(applicationId);
}


