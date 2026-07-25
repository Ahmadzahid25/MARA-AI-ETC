/**
 * MOCK DATA — pending real API contracts from backend agents.
 * Per apps/officer-workspace/AGENTS.md: "build against a clearly-marked mock
 * that matches the documented requirements (10-human-in-the-loop.md §10.4's
 * field list)."
 *
 * Document contract: shared/schemas/documents.py
 * Approval contract: shared/schemas/approval.py
 */

import type {
  DocumentExtractionRecord,
  ExtractedField,
} from '../types/documents';
import type { ApprovalRequest } from '../types/approval';
import type { ChatMessage, Task } from '../types/workspace';
import type {
  DashboardStats,
  WorkflowInstance,
  AgentMetric,
  RiskFlag,
  PendingApprovalSummary,
} from '../types/dashboard';

// ── Document Extraction Mocks ────────────────────────────────────────

const MOCK_FIELDS: ExtractedField[] = [
  {
    name: 'Applicant Name',
    value: 'Ahmad bin Abdullah',
    confidence: 0.97,
    source: 'pdf_text_layer',
    citation: {
      document_id: 'doc-001',
      page: 1,
      bounding_box: { page: 1, x: 120, y: 85, width: 200, height: 14 },
    },
  },
  {
    name: 'Business Registration Number',
    value: 'SSM 202401-123456',
    confidence: 0.92,
    source: 'pdf_text_layer',
    citation: {
      document_id: 'doc-001',
      page: 1,
      bounding_box: { page: 1, x: 120, y: 110, width: 160, height: 14 },
    },
  },
  {
    name: 'Loan Amount (MYR)',
    value: '150000',
    confidence: 0.78,
    source: 'ocr',
    citation: {
      document_id: 'doc-001',
      page: 2,
      bounding_box: { page: 2, x: 300, y: 200, width: 80, height: 14 },
    },
  },
  {
    name: 'Business Type',
    value: 'Food & Beverage Manufacturing',
    confidence: 0.64,
    source: 'ocr',
    citation: {
      document_id: 'doc-001',
      page: 1,
      bounding_box: { page: 1, x: 120, y: 135, width: 180, height: 14 },
    },
  },
  {
    name: 'Annual Revenue (MYR)',
    value: '850000',
    confidence: 0.88,
    source: 'pdf_text_layer',
    citation: {
      document_id: 'doc-001',
      page: 3,
      bounding_box: { page: 3, x: 150, y: 310, width: 100, height: 14 },
    },
  },
];

export const MOCK_EXTRACTION: DocumentExtractionRecord = {
  document_id: 'doc-001',
  classification: {
    document_type: 'Loan Application Form',
    confidence: 0.95,
  },
  fields: MOCK_FIELDS,
};

// ── Approval Request Mocks ───────────────────────────────────────────

export const MOCK_APPROVAL_REQUESTS: ApprovalRequest[] = [
  {
    id: 'apr-001',
    workflow_thread_id: 'wf-001',
    document_id: 'doc-001',
    status: 'pending',
    agent_name: 'Document Agent',
    question: 'Confirm extracted loan application details for Ahmad bin Abdullah',
    created_at: '2026-07-25T09:15:00Z',
    assigned_to: 'Officer Zahid',
  },
  {
    id: 'apr-002',
    workflow_thread_id: 'wf-002',
    document_id: 'doc-002',
    status: 'pending',
    agent_name: 'Compliance Agent',
    question: 'Acknowledge compliance exception: missing AML declaration',
    created_at: '2026-07-25T08:30:00Z',
    assigned_to: 'Officer Zahid',
  },
  {
    id: 'apr-003',
    workflow_thread_id: 'wf-003',
    document_id: 'doc-003',
    status: 'pending',
    agent_name: 'Finance Agent',
    question: 'Approve financial analysis for SME grant application',
    created_at: '2026-07-24T16:00:00Z',
    assigned_to: 'Officer Zahid',
  },
  {
    id: 'apr-004',
    workflow_thread_id: 'wf-001',
    document_id: 'doc-001',
    status: 'approved',
    agent_name: 'Document Agent',
    question: 'Confirm applicant identity verification',
    created_at: '2026-07-24T14:20:00Z',
    assigned_to: 'Officer Zahid',
  },
  {
    id: 'apr-005',
    workflow_thread_id: 'wf-004',
    document_id: 'doc-004',
    status: 'rejected',
    agent_name: 'Risk Agent',
    question: 'Approve risk assessment for high-exposure loan',
    created_at: '2026-07-23T11:00:00Z',
    assigned_to: 'Officer Zahid',
  },
];

// ── Chat Message Mocks ───────────────────────────────────────────────

export const MOCK_MESSAGES: ChatMessage[] = [
  {
    id: 'msg-001',
    role: 'user',
    content: 'Assess the loan application from Ahmad bin Abdullah for MYR 150,000',
    timestamp: '2026-07-25T09:00:00Z',
  },
  {
    id: 'msg-002',
    role: 'assistant',
    content:
      'I\'ve initiated the loan assessment workflow for Ahmad bin Abdullah. The Document Agent is extracting key fields from the application form. Low-confidence fields will need your confirmation before proceeding.',
    timestamp: '2026-07-25T09:01:00Z',
    agent_name: 'Planner Agent',
  },
  {
    id: 'msg-003',
    role: 'assistant',
    content:
      'Document extraction complete. 2 fields are below the 0.85 confidence threshold:\n- **Loan Amount (MYR)**: 150,000 (confidence: 0.78, OCR)\n- **Business Type**: Food & Beverage Manufacturing (confidence: 0.64, OCR)\n\nThese require your confirmation before the workflow can proceed.',
    timestamp: '2026-07-25T09:03:00Z',
    agent_name: 'Document Agent',
  },
  {
    id: 'msg-004',
    role: 'user',
    content: 'Confirm the loan amount, but correct the business type to "Food & Beverage Retail"',
    timestamp: '2026-07-25T09:05:00Z',
  },
  {
    id: 'msg-005',
    role: 'assistant',
    content:
      'Noted. Loan amount confirmed at MYR 150,000. Business type corrected to "Food & Beverage Retail" — this correction has been recorded and attributed to you. The workflow is now proceeding to the Compliance Agent.',
    timestamp: '2026-07-25T09:05:30Z',
    agent_name: 'Planner Agent',
  },
];

// ── Task Mocks ───────────────────────────────────────────────────────

export const MOCK_TASKS: Task[] = [
  {
    id: 'task-001',
    title: 'Document extraction — Ahmad bin Abdullah',
    status: 'completed',
    agent_name: 'Document Agent',
    created_at: '2026-07-25T09:00:00Z',
    updated_at: '2026-07-25T09:03:00Z',
    description: 'Extract key fields from loan application form',
  },
  {
    id: 'task-002',
    title: 'Compliance check — Ahmad bin Abdullah',
    status: 'awaiting_approval',
    agent_name: 'Compliance Agent',
    created_at: '2026-07-25T09:05:30Z',
    updated_at: '2026-07-25T09:10:00Z',
    description: 'Check application against compliance policies',
  },
  {
    id: 'task-003',
    title: 'Financial analysis — Ahmad bin Abdullah',
    status: 'in_progress',
    agent_name: 'Finance Agent',
    created_at: '2026-07-25T09:10:00Z',
    updated_at: '2026-07-25T09:10:00Z',
    description: 'Analyze financial projections and viability',
  },
  {
    id: 'task-004',
    title: 'Risk assessment — Ahmad bin Abdullah',
    status: 'pending',
    agent_name: 'Risk Agent',
    created_at: '2026-07-25T09:00:00Z',
    updated_at: '2026-07-25T09:00:00Z',
    description: 'Evaluate loan risk based on applicant profile',
  },
  {
    id: 'task-005',
    title: 'Recommendation generation — Ahmad bin Abdullah',
    status: 'pending',
    agent_name: 'Recommendation Agent',
    created_at: '2026-07-25T09:00:00Z',
    updated_at: '2026-07-25T09:00:00Z',
    description: 'Generate final recommendation for officer review',
  },
];

// ── Dashboard Mocks ──────────────────────────────────────────────────

export const MOCK_DASHBOARD_STATS: DashboardStats = {
  total_workflows: 24,
  active_workflows: 7,
  pending_approval_count: 3,
  blocked_workflows: 2,
  risk_flags_outstanding: 4,
};

export const MOCK_WORKFLOWS: WorkflowInstance[] = [
  {
    id: 'wf-001',
    title: 'Loan Application — Ahmad bin Abdullah',
    applicant: 'Ahmad bin Abdullah',
    status: 'in_progress',
    stage: 'Compliance Check',
    created_at: '2026-07-25T09:00:00Z',
    updated_at: '2026-07-25T09:10:00Z',
    assigned_agent: 'Compliance Agent',
    confidence: 0.82,
  },
  {
    id: 'wf-002',
    title: 'SME Grant — Sinar Sdn Bhd',
    applicant: 'Sinar Sdn Bhd',
    status: 'awaiting_approval',
    stage: 'Approval Gate',
    created_at: '2026-07-25T08:30:00Z',
    updated_at: '2026-07-25T09:15:00Z',
    assigned_agent: 'Finance Agent',
    confidence: 0.91,
  },
  {
    id: 'wf-003',
    title: 'Microloan — Fatimah binti Hassan',
    applicant: 'Fatimah binti Hassan',
    status: 'completed',
    stage: 'Completed',
    created_at: '2026-07-24T14:00:00Z',
    updated_at: '2026-07-25T08:00:00Z',
    assigned_agent: 'Document Agent',
    confidence: 0.95,
  },
  {
    id: 'wf-004',
    title: 'Business Development Grant — Maju Jaya Enterprise',
    applicant: 'Maju Jaya Enterprise',
    status: 'blocked',
    stage: 'Risk Assessment',
    created_at: '2026-07-24T10:00:00Z',
    updated_at: '2026-07-25T07:30:00Z',
    assigned_agent: 'Risk Agent',
    confidence: 0.45,
  },
  {
    id: 'wf-005',
    title: 'Equipment Financing — Restu Ibu Catering',
    applicant: 'Restu Ibu Catering',
    status: 'blocked',
    stage: 'Compliance Check',
    created_at: '2026-07-23T16:00:00Z',
    updated_at: '2026-07-24T18:00:00Z',
    assigned_agent: 'Compliance Agent',
    confidence: 0.38,
  },
  {
    id: 'wf-006',
    title: 'Startup Grant — Teknovasi Digital',
    applicant: 'Teknovasi Digital',
    status: 'pending',
    stage: 'Document Extraction',
    created_at: '2026-07-25T11:00:00Z',
    updated_at: '2026-07-25T11:00:00Z',
    assigned_agent: 'Document Agent',
    confidence: 0.0,
  },
];

export const MOCK_AGENT_METRICS: AgentMetric[] = [
  {
    agent_name: 'Document Agent',
    workflows_processed: 18,
    avg_latency_seconds: 12.4,
    total_cost: 2.45,
    avg_confidence: 0.88,
  },
  {
    agent_name: 'Compliance Agent',
    workflows_processed: 14,
    avg_latency_seconds: 28.7,
    total_cost: 4.12,
    avg_confidence: 0.79,
  },
  {
    agent_name: 'Finance Agent',
    workflows_processed: 11,
    avg_latency_seconds: 45.2,
    total_cost: 6.78,
    avg_confidence: 0.85,
  },
  {
    agent_name: 'Risk Agent',
    workflows_processed: 9,
    avg_latency_seconds: 52.1,
    total_cost: 7.33,
    avg_confidence: 0.72,
  },
  {
    agent_name: 'Recommendation Agent',
    workflows_processed: 7,
    avg_latency_seconds: 18.9,
    total_cost: 3.21,
    avg_confidence: 0.91,
  },
];

export const MOCK_RISK_FLAGS: RiskFlag[] = [
  {
    id: 'rf-001',
    workflow_id: 'wf-004',
    description: 'Loan-to-income ratio exceeds 50% threshold',
    severity: 'high',
    created_at: '2026-07-25T07:30:00Z',
    agent_name: 'Risk Agent',
    status: 'open',
  },
  {
    id: 'rf-002',
    workflow_id: 'wf-004',
    description: 'Insufficient collateral coverage (62% vs 80% minimum)',
    severity: 'critical',
    created_at: '2026-07-25T07:30:00Z',
    agent_name: 'Risk Agent',
    status: 'open',
  },
  {
    id: 'rf-003',
    workflow_id: 'wf-005',
    description: 'Missing AML declaration document',
    severity: 'high',
    created_at: '2026-07-24T18:00:00Z',
    agent_name: 'Compliance Agent',
    status: 'open',
  },
  {
    id: 'rf-004',
    workflow_id: 'wf-002',
    description: 'Business registration renewal pending (expired 30 days)',
    severity: 'medium',
    created_at: '2026-07-25T08:30:00Z',
    agent_name: 'Compliance Agent',
    status: 'acknowledged',
  },
];

export const MOCK_PENDING_APPROVALS: PendingApprovalSummary[] = [
  {
    id: 'apr-001',
    workflow_title: 'Loan Application — Ahmad bin Abdullah',
    agent_name: 'Document Agent',
    question: 'Confirm extracted loan application details',
    created_at: '2026-07-25T09:15:00Z',
    age_hours: 2.5,
    status: 'pending',
    assigned_to: 'Officer Zahid',
  },
  {
    id: 'apr-002',
    workflow_title: 'SME Grant — Sinar Sdn Bhd',
    agent_name: 'Compliance Agent',
    question: 'Acknowledge compliance exception: missing AML declaration',
    created_at: '2026-07-25T08:30:00Z',
    age_hours: 3.5,
    status: 'pending',
    assigned_to: 'Officer Zahid',
  },
  {
    id: 'apr-003',
    workflow_title: 'Business Development Grant — Maju Jaya Enterprise',
    agent_name: 'Finance Agent',
    question: 'Approve financial analysis for grant application',
    created_at: '2026-07-24T16:00:00Z',
    age_hours: 19.0,
    status: 'pending',
    assigned_to: 'Officer Zahid',
  },
];
