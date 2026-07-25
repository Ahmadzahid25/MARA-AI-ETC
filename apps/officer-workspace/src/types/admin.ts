/**
 * Admin Console types — user/role/agent configuration per
 * docs/architecture/02-system-architecture.md §2.2
 *
 * MOCK DATA — pending real API contracts from backend services.
 */

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: string;
  branch: string;
  status: 'active' | 'inactive' | 'invited';
  mfa_enrolled: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AdminRole {
  id: string;
  name: string;
  description: string;
  member_count: number;
  grants: string[];
}

export type AutonomyLevel = 'BOUNDED' | 'GUIDED' | 'EXPLORATORY';

export interface AgentProfile {
  name: string;
  description: string;
  autonomy: AutonomyLevel;
  tools: string[];
  confidence_threshold: number;
  approval_gate_required: boolean;
  model_tier: string;
  network_egress: boolean;
}

export interface SystemSetting {
  key: string;
  label: string;
  value: string | boolean | number;
  type: 'text' | 'toggle' | 'number' | 'select';
  options?: string[];
  description: string;
}
