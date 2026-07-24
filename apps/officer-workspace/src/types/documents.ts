/**
 * Document extraction contract — mirrors shared/schemas/documents.py
 * Per docs/architecture/10-human-in-the-loop.md §10.4
 */

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
  threshold = 0.85,
): ExtractedField[] {
  return fields.filter((f) => f.confidence < threshold);
}

export type ConfidenceLevel = 'green' | 'primaryDark' | 'red';

export function confidenceColor(confidence: number): ConfidenceLevel {
  if (confidence >= 0.85) return 'green';
  if (confidence >= 0.6) return 'primaryDark';
  return 'red';
}

export function confidenceLabel(confidence: number): string {
  if (confidence >= 0.85) return 'High';
  if (confidence >= 0.6) return 'Medium';
  return 'Low';
}
