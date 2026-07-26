import { useState } from 'react';
import { Button, Input, Typography } from '@openhands/ui';
import type { ExtractedField } from '../../types/documents';
import type { FieldCorrection } from '../../types/approval';

interface CorrectionFormProps {
  fields: ExtractedField[];
  onSubmit: (corrections: FieldCorrection[]) => void;
  onCancel: () => void;
}

export function CorrectionForm({
  fields,
  onSubmit,
  onCancel,
}: CorrectionFormProps) {
  const [corrections, setCorrections] = useState<
    Record<string, { value: string; reason: string }>
  >(() =>
    Object.fromEntries(
      fields.map((f) => [f.name, { value: f.value, reason: '' }]),
    ),
  );

  const hasChanges = fields.some(
    (f) => corrections[f.name]?.value !== f.value || corrections[f.name]?.reason !== '',
  );

  function handleSubmit() {
    const result: FieldCorrection[] = [];
    for (const field of fields) {
      const entry = corrections[field.name];
      if (entry && entry.value !== field.value) {
        result.push({
          field_name: field.name,
          corrected_value: entry.value,
          reason: entry.reason,
        });
      }
    }
    if (result.length > 0) {
      onSubmit(result);
    }
  }

  function updateField(fieldName: string, patch: { value?: string; reason?: string }) {
    setCorrections((prev) => {
      const existing = prev[fieldName] ?? { value: '', reason: '' };
      return {
        ...prev,
        [fieldName]: { ...existing, ...patch },
      };
    });
  }

  return (
    <div className="space-y-4 rounded-md border border-amber-200 bg-amber-50 p-4 dark:border-amber-800/60 dark:bg-amber-950/40">
      <Typography.H5 className="text-slate-900 dark:text-white">Correct Fields</Typography.H5>
      <Typography.Text fontSize="xs" className="text-gray-500 dark:text-slate-400">
        Edit the fields that need correction. The original agent output is
        preserved separately — your corrections are stored as a distinct,
        attributed record.
      </Typography.Text>

      {fields.map((field) => (
        <div key={field.name} className="space-y-1">
          <Input
            label={field.name}
            value={corrections[field.name]?.value ?? field.value}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              updateField(field.name, { value: e.target.value })
            }
          />
          <Input
            label="Correction reason (optional)"
            value={corrections[field.name]?.reason ?? ''}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
              updateField(field.name, { reason: e.target.value })
            }
          />
        </div>
      ))}

      <div className="flex gap-3">
        <Button
          variant="primary"
          onClick={handleSubmit}
          disabled={!hasChanges}
        >
          Submit Corrections
        </Button>
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
      </div>
    </div>
  );
}
