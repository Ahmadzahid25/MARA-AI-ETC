/**
 * Dashboard data contracts — read-only aggregated surface per
 * docs/architecture/02-system-architecture.md §2.2
 *
 * MOCK DATA — pending real API contracts from backend agents.
 */

import type { ApprovalRequestStatus } from './approval';
import type { TaskStatus } from './workspace';

export interface DashboardStats {
  total_workflows: number;
  active_workflows: number;
  pending_approval_count: number;
  blocked_workflows: number;
  risk_flags_outstanding: number;
}

export interface WorkflowInstance {
  id: string;
  title: string;
  applicant: string;
  status: TaskStatus;
  stage: string;
  created_at: string;
  updated_at: string;
  assigned_agent: string;
  confidence: number;
}

export interface AgentMetric {
  agent_name: string;
  workflows_processed: number;
  avg_latency_seconds: number;
  total_cost: number;
  avg_confidence: number;
}

export interface RiskFlag {
  id: string;
  workflow_id: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  created_at: string;
  agent_name: string;
  status: 'open' | 'acknowledged' | 'resolved';
}

export interface PendingApprovalSummary {
  id: string;
  workflow_title: string;
  agent_name: string;
  question: string;
  created_at: string;
  age_hours: number;
  status: ApprovalRequestStatus;
  assigned_to: string;
}
