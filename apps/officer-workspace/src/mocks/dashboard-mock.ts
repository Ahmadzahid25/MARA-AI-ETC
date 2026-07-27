/**
 * MOCK DATA — Dashboard only.
 *
 * Per apps/officer-workspace/AGENTS.md §"When something you need doesn't exist yet":
 * "build against a clearly-marked mock that matches the documented requirements ...
 * and say explicitly ... that this is a mock pending the real contract."
 *
 * These mocks exist because the Dashboard API endpoints are Milestone 1+.
 * Replace with live API calls once those endpoints are built.
 * Contracts: src/types/dashboard.ts
 */

import type {
  DashboardStats,
  WorkflowInstance,
  AgentMetric,
  RiskFlag,
  PendingApprovalSummary,
} from '../types/dashboard';

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
