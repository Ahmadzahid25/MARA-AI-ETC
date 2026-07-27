import type { DocumentExtractionRecord } from '../types/documents';
import type { ApprovalRequest, FieldCorrection } from '../types/approval';
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
  type CreateAssessmentInput,
  type DecisionInput,
} from './api';

// ─── Dashboard ────────────────────────────────────────────────

export async function fetchDashboardStats(): Promise<DashboardStats> {
  throw new Error('API not implemented for dashboard stats');
}

export async function fetchWorkflows(): Promise<WorkflowInstance[]> {
  throw new Error('API not implemented for workflows');
}

export async function fetchAgentMetrics(): Promise<AgentMetric[]> {
  throw new Error('API not implemented for agent metrics');
}

export async function fetchRiskFlags(): Promise<RiskFlag[]> {
  throw new Error('API not implemented for risk flags');
}

export async function fetchPendingApprovals(): Promise<PendingApprovalSummary[]> {
  throw new Error('API not implemented for pending approvals');
}

// ─── Workspace ─────────────────────────────────────────────────

export async function fetchMessages(): Promise<ChatMessage[]> {
  throw new Error('API not implemented for messages');
}

export async function fetchTasks(): Promise<Task[]> {
  throw new Error('API not implemented for tasks');
}

export async function startAssessment(
  input: CreateAssessmentInput,
): Promise<{ threadId: string; pendingGate: string | null }> {
  const res = await apiCreateAssessment(input);
  return { threadId: res.thread_id, pendingGate: res.pending_gate };
}

// ─── Review Console ────────────────────────────────────────────

export async function fetchApprovalRequests(): Promise<ApprovalRequest[]> {
  throw new Error('API not implemented for approval requests');
}

export async function fetchExtraction(
  _documentId: string,
): Promise<DocumentExtractionRecord> {
  throw new Error('API not implemented for document extraction');
}

export async function submitGateDecision(
  threadId: string,
  action: 'approve' | 'reject' | 'correct',
  reason?: string,
  corrections?: FieldCorrection[],
): Promise<{ success: boolean; actedGate: string | null }> {
  const input: DecisionInput = { action, reason };
  if (corrections) input.corrections = corrections.map((c) => ({
    field_name: c.field_name,
    corrected_value: c.corrected_value,
    reason: c.reason,
  }));
  const res = await apiSubmitDecision(threadId, input);
  return { success: true, actedGate: res.acted_gate };
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
