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
  listOfficerApplications,
} from './api';

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
    confidence: 0,
  };
}

async function fetchOfficerQueueItems(): Promise<V1OfficerQueueItem[]> {
  const queue = await listOfficerApplications();
  return queue.items ?? [];
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
  throw new Error('API not implemented for agent metrics');
}

export async function fetchRiskFlags(): Promise<RiskFlag[]> {
  const items = await fetchOfficerQueueItems();
  return items
    .filter((item) => item.status === 'NEEDS_INFO')
    .map((item) => ({
      id: `risk-${item.application_id}`,
      workflow_id: item.application_id,
      description: `${item.scheme}: additional information required before progression`,
      severity: 'medium' as const,
      created_at: item.updated_at,
      agent_name: 'Recommendation Agent',
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
        question: 'Do you approve this application recommendation?',
        created_at: item.updated_at,
        age_hours: ageHours,
        status: 'pending' as const,
        assigned_to: 'Officer',
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

// ─── Review Console ────────────────────────────────────────────

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

export function extractGateRole(detail: string): string | null {
  const match = detail.match(/requires\s+(\w+(?:\s+\w+)*)/i);
  return match ? match[1] ?? null : null;
}

export { ApiError };

// ─── Admin Console ─────────────────────────────────────────────

export async function fetchUsers(): Promise<AdminUser[]> {
  throw new Error('API not implemented for users');
}

export async function fetchRoles(): Promise<AdminRole[]> {
  throw new Error('API not implemented for roles');
}

export async function fetchAgentProfiles(): Promise<AgentProfile[]> {
  throw new Error('API not implemented for agent profiles');
}

export async function fetchSystemSettings(): Promise<SystemSetting[]> {
  throw new Error('API not implemented for system settings');
}
