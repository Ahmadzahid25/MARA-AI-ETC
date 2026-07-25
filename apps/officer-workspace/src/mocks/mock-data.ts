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
import type { AdminUser, AdminRole, AgentProfile, SystemSetting } from '../types/admin';

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

// ── Admin Console Mocks ──────────────────────────────────────────────

export const MOCK_USERS: AdminUser[] = [
  {
    id: 'usr-001',
    name: 'Zahid Abdullah',
    email: 'zahid@mara.gov.my',
    role: 'Entrepreneurship Officer',
    branch: 'Kuala Lumpur',
    status: 'active',
    mfa_enrolled: true,
    created_at: '2026-01-15T00:00:00Z',
    last_login: '2026-07-25T09:00:00Z',
  },
  {
    id: 'usr-002',
    name: 'Siti Aishah',
    email: 'siti@mara.gov.my',
    role: 'Compliance Officer',
    branch: 'Selangor',
    status: 'active',
    mfa_enrolled: true,
    created_at: '2026-02-01T00:00:00Z',
    last_login: '2026-07-24T16:30:00Z',
  },
  {
    id: 'usr-003',
    name: 'Ahmad Faizal',
    email: 'ahmad.f@mara.gov.my',
    role: 'Risk Officer',
    branch: 'Penang',
    status: 'active',
    mfa_enrolled: false,
    created_at: '2026-03-10T00:00:00Z',
    last_login: '2026-07-23T11:15:00Z',
  },
  {
    id: 'usr-004',
    name: 'Nurul Huda',
    email: 'nurul@mara.gov.my',
    role: 'Branch Manager',
    branch: 'Johor',
    status: 'active',
    mfa_enrolled: true,
    created_at: '2025-11-01T00:00:00Z',
    last_login: '2026-07-25T07:45:00Z',
  },
  {
    id: 'usr-005',
    name: 'Lim Wei Ming',
    email: 'weiming@mara.gov.my',
    role: 'Finance Officer',
    branch: 'Perak',
    status: 'inactive',
    mfa_enrolled: true,
    created_at: '2026-01-20T00:00:00Z',
    last_login: '2026-06-30T00:00:00Z',
  },
  {
    id: 'usr-006',
    name: 'Fatimah Hassan',
    email: 'fatimah.h@mara.gov.my',
    role: 'Administrator',
    branch: 'HQ',
    status: 'active',
    mfa_enrolled: true,
    created_at: '2024-06-01T00:00:00Z',
    last_login: '2026-07-25T08:00:00Z',
  },
  {
    id: 'usr-007',
    name: 'Roslan Bakar',
    email: 'roslan@mara.gov.my',
    role: 'Entrepreneurship Officer',
    branch: 'Sabah',
    status: 'invited',
    mfa_enrolled: false,
    created_at: '2026-07-20T00:00:00Z',
    last_login: null,
  },
];

export const MOCK_ROLES: AdminRole[] = [
  {
    id: 'role-001',
    name: 'Entrepreneurship Officer',
    description: 'Frontline officer managing applicant workflows and document review',
    member_count: 12,
    grants: ['Workspace', 'Review Console', 'Dashboard'],
  },
  {
    id: 'role-002',
    name: 'Compliance Officer',
    description: 'Reviews compliance exceptions and AML declarations',
    member_count: 4,
    grants: ['Review Console', 'Dashboard', 'Admin Console (read-only)'],
  },
  {
    id: 'role-003',
    name: 'Finance Officer',
    description: 'Financial analysis and budget approval',
    member_count: 3,
    grants: ['Review Console', 'Dashboard'],
  },
  {
    id: 'role-004',
    name: 'Risk Officer',
    description: 'Risk assessment and flag management',
    member_count: 3,
    grants: ['Review Console', 'Dashboard'],
  },
  {
    id: 'role-005',
    name: 'Branch Manager',
    description: 'Portfolio oversight, delegation of authority, escalation point',
    member_count: 8,
    grants: ['Dashboard', 'Review Console', 'Admin Console (read-only)'],
  },
  {
    id: 'role-006',
    name: 'Administrator',
    description: 'System-wide user/role/agent configuration',
    member_count: 2,
    grants: ['Admin Console', 'Dashboard'],
  },
  {
    id: 'role-007',
    name: 'Auditor',
    description: 'Cross-workflow read access for compliance auditing',
    member_count: 2,
    grants: ['Dashboard', 'Audit Log'],
  },
];

export const MOCK_AGENT_PROFILES: AgentProfile[] = [
  {
    name: 'Document Agent',
    description: 'Extracts and classifies document fields from uploaded files',
    autonomy: 'GUIDED',
    tools: ['pdf_parser', 'ocr', 'classification'],
    confidence_threshold: 0.85,
    approval_gate_required: true,
    model_tier: 'Sonnet',
    network_egress: false,
  },
  {
    name: 'Compliance Agent',
    description: 'Checks applications against regulatory policies and flags exceptions',
    autonomy: 'GUIDED',
    tools: ['policy_engine', 'aml_check', 'sanctions_screening'],
    confidence_threshold: 0.9,
    approval_gate_required: true,
    model_tier: 'Sonnet',
    network_egress: false,
  },
  {
    name: 'Finance Agent',
    description: 'Analyses financial projections, cash flow, and repayment capacity',
    autonomy: 'BOUNDED',
    tools: ['financial_analyzer', 'ratio_calculator', 'projection_model'],
    confidence_threshold: 0.8,
    approval_gate_required: true,
    model_tier: 'Sonnet',
    network_egress: false,
  },
  {
    name: 'Risk Agent',
    description: 'Evaluates loan risk, collateral adequacy, and exposure limits',
    autonomy: 'BOUNDED',
    tools: ['risk_scorer', 'collateral_evaluator', 'exposure_checker'],
    confidence_threshold: 0.85,
    approval_gate_required: false,
    model_tier: 'Sonnet',
    network_egress: false,
  },
  {
    name: 'Market Agent',
    description: 'Gathers market intelligence, comparable data, and economic indicators',
    autonomy: 'EXPLORATORY',
    tools: ['web_search', 'data_feed_ingestor', 'sentiment_analyzer'],
    confidence_threshold: 0.7,
    approval_gate_required: false,
    model_tier: 'Haiku',
    network_egress: true,
  },
  {
    name: 'Recommendation Agent',
    description: 'Generates final funding recommendation synthesising all agent outputs',
    autonomy: 'GUIDED',
    tools: ['aggregator', 'scoring_model', 'report_generator'],
    confidence_threshold: 0.9,
    approval_gate_required: true,
    model_tier: 'Opus',
    network_egress: false,
  },
  {
    name: 'Planner Agent',
    description: 'Orchestrates multi-agent workflows, delegates tasks, tracks progress',
    autonomy: 'GUIDED',
    tools: ['workflow_engine', 'agent_dispatcher', 'progress_tracker'],
    confidence_threshold: 0.85,
    approval_gate_required: false,
    model_tier: 'Sonnet',
    network_egress: false,
  },
];

export const MOCK_SYSTEM_SETTINGS: SystemSetting[] = [
  {
    key: 'llm_default_provider',
    label: 'Default LLM Provider',
    value: 'LiteLLM',
    type: 'text',
    description: 'Default LLM routing provider for all agent inference',
  },
  {
    key: 'approval_gate_enabled',
    label: 'Approval Gates Enabled',
    value: true,
    type: 'toggle',
    description: 'Master toggle for human-in-the-loop approval gates',
  },
  {
    key: 'max_loan_exposure',
    label: 'Max Loan Exposure (MYR)',
    value: 5000000,
    type: 'number',
    description: 'Maximum loan exposure requiring Branch Manager sign-off',
  },
  {
    key: 'confidence_threshold_default',
    label: 'Default Confidence Threshold',
    value: 0.8,
    type: 'number',
    description: 'Default confidence threshold for agent outputs',
  },
  {
    key: 'audit_retention_days',
    label: 'Audit Retention Period (days)',
    value: 365,
    type: 'number',
    description: 'Number of days audit records are retained',
  },
  {
    key: 'mfa_required_for_approval',
    label: 'MFA Required for Approval Actions',
    value: true,
    type: 'toggle',
    description: 'Require MFA for any Approve/Reject/Correct action',
  },
  {
    key: 'document_classification_default',
    label: 'Default Document Sensitivity',
    value: 'Internal',
    type: 'select',
    options: ['Public', 'Internal', 'Confidential', 'Restricted'],
    description: 'Default classification for uploaded documents',
  },
];
