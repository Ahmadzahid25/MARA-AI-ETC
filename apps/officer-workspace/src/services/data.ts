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

const MOCK_QUEUE_ITEMS: V1OfficerQueueItem[] = [
  {
    application_id: 'APP-2026-001',
    applicant_name: 'Ahmad bin Razak',
    scheme: 'MARA Skim Pembiayaan Kontrak (SPiKE)',
    amount_requested: 150000,
    status: 'UNDER_REVIEW',
    updated_at: new Date(Date.now() - 3600000 * 2).toISOString(),
  },
  {
    application_id: 'APP-2026-002',
    applicant_name: 'Siti Nurhaliza Enterprise',
    scheme: 'Skim Pembiayaan Perniagaan Muda',
    amount_requested: 85000,
    status: 'PROCESSING',
    updated_at: new Date(Date.now() - 3600000 * 8).toISOString(),
  },
  {
    application_id: 'APP-2026-003',
    applicant_name: 'Tan Brothers Hardware Sdn Bhd',
    scheme: 'MARA Skim Pembiayaan Utama (SPU)',
    amount_requested: 300000,
    status: 'NEEDS_INFO',
    updated_at: new Date(Date.now() - 3600000 * 18).toISOString(),
  },
  {
    application_id: 'APP-2026-004',
    applicant_name: 'Kedai Runcit Kasih Ibu',
    scheme: 'Skim Pembiayaan Mikro MARA',
    amount_requested: 25000,
    status: 'APPROVED',
    updated_at: new Date(Date.now() - 3600000 * 36).toISOString(),
  },
];

const MOCK_USERS: AdminUser[] = [
  { id: 'usr-1', name: 'Pegawai Semakan MARA', email: 'officer@mara.local', role: 'Officer', branch: 'HQ Kuala Lumpur', status: 'active', mfa_enrolled: true, created_at: '2026-01-01T00:00:00Z', last_login: '2026-07-29T10:00:00Z' },
  { id: 'usr-2', name: 'Pentadbir Sistem MARA', email: 'admin@mara.local', role: 'Admin', branch: 'HQ Kuala Lumpur', status: 'active', mfa_enrolled: true, created_at: '2026-01-01T00:00:00Z', last_login: '2026-07-29T09:15:00Z' },
  { id: 'usr-3', name: 'Pegawai Risiko', email: 'risk@mara.local', role: 'Risk Officer', branch: 'HQ Kuala Lumpur', status: 'active', mfa_enrolled: false, created_at: '2026-02-15T00:00:00Z', last_login: '2026-07-28T16:30:00Z' },
];

const MOCK_ROLES: AdminRole[] = [
  { id: 'role-1', name: 'Officer', description: 'Pegawai penilai permohonan', member_count: 12, grants: ['view_applications', 'submit_decisions', 'upload_documents'] },
  { id: 'role-2', name: 'Risk Officer', description: 'Pegawai pengurusan risiko', member_count: 4, grants: ['view_applications', 'risk_signoff'] },
  { id: 'role-3', name: 'Admin', description: 'Pentadbir sistem penuh', member_count: 2, grants: ['all'] },
];

const MOCK_AGENT_PROFILES: AgentProfile[] = [
  { name: 'Document Agent', description: 'Ekstraksi dokumen & OCR', autonomy: 'BOUNDED', tools: ['ocr', 'parser'], confidence_threshold: 0.85, approval_gate_required: true, model_tier: 'fast', network_egress: false },
  { name: 'Compliance Agent', description: 'Semakan pematuhan syara & dasar MARA', autonomy: 'GUIDED', tools: ['compliance_rules'], confidence_threshold: 0.90, approval_gate_required: true, model_tier: 'standard', network_egress: false },
  { name: 'Finance Agent', description: 'Analisis nisbah kewangan & bank statement', autonomy: 'GUIDED', tools: ['finance_calculator'], confidence_threshold: 0.88, approval_gate_required: true, model_tier: 'standard', network_egress: false },
  { name: 'Risk Agent', description: 'Penilaian risiko kredit & kebankrapan', autonomy: 'BOUNDED', tools: ['risk_matrix'], confidence_threshold: 0.85, approval_gate_required: true, model_tier: 'standard', network_egress: true },
  { name: 'Market Agent', description: 'Semakan pasaran & trend sektor', autonomy: 'EXPLORATORY', tools: ['web_search'], confidence_threshold: 0.80, approval_gate_required: true, model_tier: 'advanced', network_egress: true },
  { name: 'Recommendation Agent', description: 'Penjanaan syor pembiayaan akhir', autonomy: 'GUIDED', tools: ['recommender'], confidence_threshold: 0.90, approval_gate_required: true, model_tier: 'advanced', network_egress: false },
  { name: 'Planner Agent', description: 'Pengurusan alur kerja agentic', autonomy: 'BOUNDED', tools: ['workflow_orchestrator'], confidence_threshold: 0.95, approval_gate_required: false, model_tier: 'fast', network_egress: false },
];

const MOCK_SYSTEM_SETTINGS: SystemSetting[] = [
  { key: 'MOCK_FALLBACK_ENABLED', label: 'Fallback Data Olok-olok', value: true, type: 'toggle', description: 'Guna data fallback jika backend 503 / tiada OCR' },
  { key: 'MAX_LOAN_AMOUNT', label: 'Had Maksimum Pembiayaan (RM)', value: 500000, type: 'number', description: 'Had maksimum pembiayaan tanpa kelulusan Khas' },
  { key: 'AUTO_RISK_THRESHOLD', label: 'Ambang Risiko Automatik', value: 0.75, type: 'number', description: 'Ambang skor keyakinan risiko untuk kelulusan automatik' },
];

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
    return MOCK_QUEUE_ITEMS;
  }
  try {
    const queue = await listOfficerApplications();
    if (queue.items && queue.items.length > 0) {
      return queue.items;
    }
  } catch (err) {
    console.warn('API /api/v1/officer/applications gagal, menggunakan data fallback:', err);
  }
  return MOCK_QUEUE_ITEMS;
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
  return MOCK_AGENT_PROFILES.map((ag) => ({
    agent_name: ag.name,
    workflows_processed: 120,
    avg_latency_seconds: 1.5,
    total_cost: 0.05,
    avg_confidence: ag.confidence_threshold,
  }));
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
    if (useMockMode || err instanceof ApiError) {
      // Fallback mock update
      const item = MOCK_QUEUE_ITEMS.find((q) => q.application_id === applicationId);
      if (item) {
        item.status = action === 'approve' ? 'APPROVED' : action === 'reject' ? 'REJECTED' : 'NEEDS_INFO';
        item.updated_at = new Date().toISOString();
      }
      return {
        application_id: applicationId,
        status: action === 'approve' ? ('APPROVED' as const) : action === 'reject' ? ('REJECTED' as const) : ('NEEDS_INFO' as const),
        decision_recorded_at: new Date().toISOString(),
      };
    }
    throw err;
  }
}

export function extractGateRole(detail: string): string | null {
  const match = detail.match(/requires\s+(\w+(?:\s+\w+)*)/i);
  return match ? match[1] ?? null : null;
}

export { ApiError };

// ─── Admin Console ─────────────────────────────────────────────

export async function fetchUsers(): Promise<AdminUser[]> {
  return MOCK_USERS;
}

export async function fetchRoles(): Promise<AdminRole[]> {
  return MOCK_ROLES;
}

export async function fetchAgentProfiles(): Promise<AgentProfile[]> {
  return MOCK_AGENT_PROFILES;
}

export async function fetchSystemSettings(): Promise<SystemSetting[]> {
  return MOCK_SYSTEM_SETTINGS;
}

// ─── Detail Application Fetch (FE-P3) ─────────────────────────

export async function getApplicationDetailWithFallback(
  applicationId: string,
): Promise<V1ApplicationDetailOutput> {
  try {
    return await apiGetApplicationDetail(applicationId);
  } catch {
    const queueItem = MOCK_QUEUE_ITEMS.find((item) => item.application_id === applicationId) ?? MOCK_QUEUE_ITEMS[0];
    const item = queueItem ?? {
      application_id: applicationId,
      applicant_name: 'Pemohon Contoh',
      scheme: 'MARA Skim Pembiayaan Perniagaan Muda',
      amount_requested: 50000,
      status: 'UNDER_REVIEW' as const,
      updated_at: new Date().toISOString(),
    };
    return {
      application_id: item.application_id,
      status: item.status,
      applicant: {
        full_name: item.applicant_name,
        ic_number: '880112-14-5543',
        phone: '012-3456789',
        email: 'pemohon@mara.gov.my',
        state: 'Wilayah Persekutuan Kuala Lumpur',
      },
      business: {
        business_name: item.applicant_name,
        ssm_number: '202101004321',
        sector: 'Perdagangan & Perkhidmatan',
        years_operating: 3,
        monthly_revenue_avg: 45000,
      },
      financing: {
        scheme: item.scheme,
        amount_requested: item.amount_requested,
        purpose: 'Pembelian stok perniagaan & modal kerja',
        tenure_months: 36,
      },
      documents: [
        { doc_type: 'SSM_CERTIFICATE', file_name: 'ssm_cert.pdf', mime_type: 'application/pdf', file_path: '/docs/ssm_cert.pdf' },
        { doc_type: 'BANK_STATEMENT', file_name: 'bank_statement_6m.pdf', mime_type: 'application/pdf', file_path: '/docs/bank_statement_6m.pdf' },
        { doc_type: 'IDENTITY_COPY', file_name: 'ic_copy.pdf', mime_type: 'application/pdf', file_path: '/docs/ic_copy.pdf' },
      ],
      ai_assessment: {
        extraction_confidence: 0.94,
        compliance_status: 'pass',
        risk_rating: 'low',
        recommendation: {
          suggested_action: 'approve',
          rationale: 'Syarikat mempunyai rekod kewangan yang kukuh dan tiada tunggakan kredit.',
          has_acknowledged_violation: false,
        },
      },
      workflow: {
        current_stage: item.status,
        updated_at: item.updated_at,
      },
    };
  }
}


