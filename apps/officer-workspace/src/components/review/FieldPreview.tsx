import { Chip, Typography } from '@openhands/ui';
import type { ExtractedField } from '../../types/documents';
import { confidenceColor, confidenceLabel } from '../../types/documents';

interface FieldPreviewProps {
  field: ExtractedField;
  corrected?: string | null;
}

export function FieldPreview({ field, corrected }: FieldPreviewProps) {
  const color = confidenceColor(field.confidence);
  const label = confidenceLabel(field.confidence);
  const sourceLabel =
    field.source === 'ocr' ? 'OCR' : 'PDF Text Layer';

  return (
    <div className="rounded-md border border-gray-200 bg-white p-3 dark:border-[#222328] dark:bg-[#18191C]">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Typography.Text fontSize="xs" fontWeight={600} className="text-slate-900 dark:text-slate-100">
              {field.name}
            </Typography.Text>
            <Chip color={color as 'green' | 'primaryDark' | 'red'} variant="pill">
              {label} ({(field.confidence * 100).toFixed(0)}%)
            </Chip>
            <Chip color="gray" variant="pill">
              {sourceLabel}
            </Chip>
          </div>

          <div className="mt-2">
            <Typography.Text fontSize="s" className="text-slate-800 dark:text-slate-200">
              {corrected !== null && corrected !== undefined ? (
                <>
                  <span className="text-gray-400 dark:text-slate-500 line-through">
                    {field.value}
                  </span>
                  {' → '}
                  <span className="font-medium text-green-700 dark:text-emerald-400">
                    {corrected}
                  </span>
                </>
              ) : (
                field.value
              )}
            </Typography.Text>
          </div>

          <div className="mt-2 flex items-center gap-2">
            <Typography.Text fontSize="xxs" className="text-gray-400 dark:text-slate-500">
              Source: {field.citation.document_id} p.{field.citation.page}
            </Typography.Text>
            {field.citation.bounding_box && (
              <Typography.Text fontSize="xxs" className="text-gray-400 dark:text-slate-500">
                Region: ({field.citation.bounding_box.x},{" "}
                {field.citation.bounding_box.y})
              </Typography.Text>
            )}
            <button className="text-xs font-medium text-blue-600 dark:text-indigo-400 hover:underline cursor-pointer">
              View source document →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
