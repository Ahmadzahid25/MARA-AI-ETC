export type TrustTier = 'approved' | 'provisional';

export interface PolicyCitation {
  document_id: string;
  version: string;
  locator: string;
  relevance: number | null;
  superseded_on: string | null;
  trust_tier: TrustTier;
}

export interface RetrievalResult {
  chunks: PolicyCitation[];
  no_confident_match: boolean;
  withheld_below_threshold: number;
  withheld_unverified: number;
  withheld_expired: number;
}

export function isProvisional(citation: PolicyCitation): boolean {
  return citation.trust_tier === 'provisional';
}

export function isStaleAsOf(citation: PolicyCitation, asOf: string): boolean {
  if (!citation.superseded_on) return false;
  return citation.superseded_on <= asOf;
}

export function needsFreshSearch(result: RetrievalResult): boolean {
  return result.withheld_expired > 0 && result.chunks.length === 0;
}

export function hasAnyWithheld(result: RetrievalResult): boolean {
  return result.withheld_below_threshold > 0
    || result.withheld_unverified > 0
    || result.withheld_expired > 0;
}
