export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  agent_name?: string;
  audio_url?: string;
  audio_duration?: number;
}

export interface DictationState {
  isRecording: boolean;
  transcript: string;
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'awaiting_approval' | 'blocked' | 'failed';

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  agent_name: string;
  created_at: string;
  updated_at: string;
  description?: string;
}

/**
 * Live assessment tracked locally — there is no GET endpoint for
 * assessment state; state is captured from POST responses and stored
 * in AssessmentContext (+ sessionStorage for refresh survival).
 */

import type { PendingGate, StageLogEntry } from '../services/api';

export interface LiveAssessment {
  thread_id: string;
  title: string;
  status: 'pending_approval' | 'completed';
  pending_gate: PendingGate | null;
  pending_payload: Record<string, unknown> | null;
  stage_log: StageLogEntry[];
  acted_gate: PendingGate | null;
  created_at: string;
}
