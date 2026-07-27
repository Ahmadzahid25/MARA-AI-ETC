import { getAccessToken } from './auth';
import { API } from '../constants';

const API_BASE = import.meta.env.VITE_API_GATEWAY_URL ?? API.BASE_PATH;

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: string,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = await getAccessToken();
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (res.status === 403) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(403, 'Gate requires a different role', body.detail);
  }

  if (res.status === 503) {
    throw new ApiError(503, 'OCR/document-classifier engine not available');
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      body.message ?? body.detail ?? `Request failed (${res.status})`,
      body.detail,
    );
  }

  return res.json() as Promise<T>;
}

// ─── Loan Assessment API ─────────────────────────────────────────

export type PendingGate =
  | 'confirm_extraction'
  | 'compliance_acknowledgment'
  | 'financial_sign_off'
  | 'risk_review'
  | 'recommendation_approval'
  | 'publish_approval';

export interface AssessmentResponse {
  thread_id: string;
  status: 'pending_approval' | 'completed';
  pending_gate: PendingGate | null;
  pending_payload: Record<string, unknown> | null;
  stage_log: StageLogEntry[];
  acted_gate: PendingGate | null;
}

export interface StageLogEntry {
  stage: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  agent: string;
  result: Record<string, unknown> | null;
}

export interface CreateAssessmentInput {
  file: File;
  sector: string;
  region: string;
  compliance_requirements?: string[];
  product_query?: string;
  precedent_query?: string;
}

export interface DecisionInput {
  action: 'approve' | 'reject' | 'correct';
  reason?: string;
  corrections?: {
    field_name: string;
    corrected_value: string;
    reason: string;
  }[];
}

export async function createAssessment(
  input: CreateAssessmentInput,
): Promise<AssessmentResponse> {
  const formData = new FormData();
  formData.append('file', input.file);
  formData.append('sector', input.sector);
  formData.append('region', input.region);
  if (input.compliance_requirements?.length) {
    for (const req of input.compliance_requirements) {
      formData.append('compliance_requirements[]', req);
    }
  }
  if (input.product_query) formData.append('product_query', input.product_query);
  if (input.precedent_query) formData.append('precedent_query', input.precedent_query);

  return request<AssessmentResponse>('/loans/assessments', {
    method: 'POST',
    body: formData,
  });
}

export async function submitDecision(
  threadId: string,
  input: DecisionInput,
): Promise<AssessmentResponse> {
  return request<AssessmentResponse>(
    `/loans/assessments/${threadId}/decision`,
    {
      method: 'POST',
      body: JSON.stringify(input),
    },
  );
}
