/**
 * Per-gate pending_payload types — mirrors shared/schemas/
 * These describe the shape of `pending_payload` for each gate.
 */

import type { Citation } from './documents';
import type { PolicyCitation, RetrievalResult } from './knowledge';

export interface ExtractionPayload {
  document_id: string;
  classification: { document_type: string; confidence: number };
  fields: Array<{
    name: string;
    value: string;
    confidence: number;
    source: string;
    citation: Citation;
  }>;
}

export interface CompliancePayload {
  document_id: string;
  retrieval_result: RetrievalResult | null;
  items: Array<{
    requirement: string;
    status: 'pass' | 'fail' | 'exception' | 'no_policy_found';
    policy_citation: PolicyCitation | null;
    notes?: string;
  }>;
}

export interface FinancialPayload {
  summary: string;
  metrics?: Record<string, number>;
  confidence: number;
}

export interface RiskPayload {
  rating: string;
  score: number;
  flags?: Array<{
    description: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
  }>;
}

export interface RecommendationPayload {
  decision: string;
  rationale: string;
  confidence: number;
}

export interface PublishPayload {
  documents: string[];
  status: string;
}
