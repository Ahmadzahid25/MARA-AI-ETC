import type { DocumentExtractionRecord, ExtractedField } from '../types/documents';
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
import {
  MOCK_EXTRACTION,
  MOCK_APPROVAL_REQUESTS,
  MOCK_MESSAGES,
  MOCK_TASKS,
  MOCK_DASHBOARD_STATS,
  MOCK_WORKFLOWS,
  MOCK_AGENT_METRICS,
  MOCK_RISK_FLAGS,
  MOCK_PENDING_APPROVALS,
  MOCK_USERS,
  MOCK_ROLES,
  MOCK_AGENT_PROFILES,
  MOCK_SYSTEM_SETTINGS,
} from '../mocks/mock-data';

type UseMock = boolean;
let useMock: UseMock = true;

export function setUseMock(val: boolean) {
  useMock = val;
}

export function isUsingMock(): boolean {
  return useMock;
}

// ─── Dashboard ────────────────────────────────────────────────

export async function fetchDashboardStats(): Promise<DashboardStats> {
  if (useMock) return MOCK_DASHBOARD_STATS;
  throw new Error('API not implemented for dashboard stats');
}

export async function fetchWorkflows(): Promise<WorkflowInstance[]> {
  if (useMock) return MOCK_WORKFLOWS;
  throw new Error('API not implemented for workflows');
}

export async function fetchAgentMetrics(): Promise<AgentMetric[]> {
  if (useMock) return MOCK_AGENT_METRICS;
  throw new Error('API not implemented for agent metrics');
}

export async function fetchRiskFlags(): Promise<RiskFlag[]> {
  if (useMock) return MOCK_RISK_FLAGS;
  throw new Error('API not implemented for risk flags');
}

export async function fetchPendingApprovals(): Promise<PendingApprovalSummary[]> {
  if (useMock) return MOCK_PENDING_APPROVALS;
  throw new Error('API not implemented for pending approvals');
}

// ─── Workspace ─────────────────────────────────────────────────

export async function fetchMessages(): Promise<ChatMessage[]> {
  if (useMock) return MOCK_MESSAGES;
  throw new Error('API not implemented for messages');
}

export async function fetchTasks(): Promise<Task[]> {
  if (useMock) return MOCK_TASKS;
  throw new Error('API not implemented for tasks');
}

export async function startAssessment(
  input: CreateAssessmentInput,
): Promise<{ threadId: string; pendingGate: string | null }> {
  if (!useMock) {
    const res = await apiCreateAssessment(input);
    return { threadId: res.thread_id, pendingGate: res.pending_gate };
  }

  await new Promise((r) => setTimeout(r, 1500));
  return {
    threadId: `wf-${Date.now()}`,
    pendingGate: 'confirm_extraction',
  };
}

// ─── Review Console ────────────────────────────────────────────

export async function fetchApprovalRequests(): Promise<ApprovalRequest[]> {
  if (useMock) return MOCK_APPROVAL_REQUESTS;
  throw new Error('API not implemented for approval requests');
}

export async function fetchExtraction(
  _documentId: string,
): Promise<DocumentExtractionRecord> {
  if (useMock) return MOCK_EXTRACTION;
  return MOCK_EXTRACTION;
}

export async function submitGateDecision(
  threadId: string,
  action: 'approve' | 'reject' | 'correct',
  reason?: string,
  corrections?: FieldCorrection[],
): Promise<{ success: boolean; actedGate: string | null }> {
  if (!useMock) {
    const input: DecisionInput = { action, reason };
    if (corrections) input.corrections = corrections.map((c) => ({
      field_name: c.field_name,
      corrected_value: c.corrected_value,
      reason: c.reason,
    }));
    const res = await apiSubmitDecision(threadId, input);
    return { success: true, actedGate: res.acted_gate };
  }

  await new Promise((r) => setTimeout(r, 800));
  return { success: true, actedGate: null };
}

export function extractGateRole(detail: string): string | null {
  const match = detail.match(/requires\s+(\w+(?:\s+\w+)*)/i);
  return match ? match[1] ?? null : null;
}

export { ApiError };

// ─── Admin Console ─────────────────────────────────────────────

export async function fetchUsers(): Promise<AdminUser[]> {
  if (useMock) return MOCK_USERS;
  throw new Error('API not implemented for users');
}

export async function fetchRoles(): Promise<AdminRole[]> {
  if (useMock) return MOCK_ROLES;
  throw new Error('API not implemented for roles');
}

export async function fetchAgentProfiles(): Promise<AgentProfile[]> {
  if (useMock) return MOCK_AGENT_PROFILES;
  throw new Error('API not implemented for agent profiles');
}

export async function fetchSystemSettings(): Promise<SystemSetting[]> {
  if (useMock) return MOCK_SYSTEM_SETTINGS;
  throw new Error('API not implemented for system settings');
}
