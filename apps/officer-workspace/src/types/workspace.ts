export type MessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  agent_name?: string;
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'awaiting_approval' | 'failed';

export interface Task {
  id: string;
  title: string;
  status: TaskStatus;
  agent_name: string;
  created_at: string;
  updated_at: string;
  description?: string;
}
