import { CONFIDENCE } from '../constants';

export type ExtractionSource = 'pdf_text_layer' | 'ocr';

export interface BoundingBox {
  page: number;
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Citation {
  document_id: string;
  page: number;
  bounding_box: BoundingBox | null;
}

export interface ExtractedField {
  name: string;
  value: string;
  confidence: number;
  source: ExtractionSource;
  citation: Citation;
}

export interface DocumentClassification {
  document_type: string;
  confidence: number;
}

export interface DocumentExtractionRecord {
  document_id: string;
  classification: DocumentClassification;
  fields: ExtractedField[];
}

export function lowConfidenceFields(
  fields: ExtractedField[],
  threshold = CONFIDENCE.HIGH_THRESHOLD,
): ExtractedField[] {
  return fields.filter((f) => f.confidence < threshold);
}

export type ConfidenceLevel = 'green' | 'primaryDark' | 'red';

export function confidenceColor(confidence: number): ConfidenceLevel {
  if (confidence >= CONFIDENCE.HIGH_THRESHOLD) return 'green';
  if (confidence >= CONFIDENCE.MEDIUM_THRESHOLD) return 'primaryDark';
  return 'red';
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= CONFIDENCE.HIGH_THRESHOLD) return CONFIDENCE.HIGH_LABEL;
  if (confidence >= CONFIDENCE.MEDIUM_THRESHOLD) return CONFIDENCE.MEDIUM_LABEL;
  return CONFIDENCE.LOW_LABEL;
}
