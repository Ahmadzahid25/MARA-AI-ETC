/**
 * Approval decision contract — mirrors shared/schemas/approval.py
 * Per docs/architecture/10-human-in-the-loop.md §10.5
 */

export type ApprovalAction = 'approve' | 'reject' | 'correct';

export interface FieldCorrection {
  field_name: string;
  corrected_value: string;
  reason: string;
}

export interface ApprovalDecisionInput {
  action: ApprovalAction;
  actor: string;
  reason: string;
  corrections: FieldCorrection[];
}

export type ApprovalRequestStatus = 'pending' | 'approved' | 'rejected' | 'corrected';

export interface ApprovalRequest {
  id: string;
  workflow_thread_id: string;
  document_id: string;
  status: ApprovalRequestStatus;
  agent_name: string;
  question: string;
  created_at: string;
  assigned_to: string;
}
