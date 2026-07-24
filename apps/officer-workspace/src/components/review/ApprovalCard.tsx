import { useState } from 'react';
import { Button, Chip, Divider, Input, Typography } from '@openhands/ui';
import type { ExtractedField } from '../../types/documents';
import type { ApprovalRequest } from '../../types/approval';
import type { FieldCorrection } from '../../types/approval';
import { FieldPreview } from './FieldPreview';
import { CorrectionForm } from './CorrectionForm';

interface ApprovalCardProps {
  request: ApprovalRequest;
  fields: ExtractedField[];
  onDecision: (
    requestId: string,
    action: 'approve' | 'reject' | 'correct',
    reason: string,
    corrections?: FieldCorrection[],
  ) => void;
}

export function ApprovalCard({
  request,
  fields,
  onDecision,
}: ApprovalCardProps) {
  const [showCorrection, setShowCorrection] = useState(false);
  const [reason, setReason] = useState('');

  const lowConfidenceFields = fields.filter((f) => f.confidence < 0.85);

  function handleApprove() {
    onDecision(request.id, 'approve', reason);
  }

  function handleReject() {
    onDecision(request.id, 'reject', reason);
  }

  function handleCorrect(corrections: FieldCorrection[]) {
    onDecision(request.id, 'correct', reason, corrections);
    setShowCorrection(false);
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm">
      <div className="border-b px-6 py-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Typography.H4>{request.agent_name}</Typography.H4>
              <Chip color="primaryDark" variant="corner">
                {request.status}
              </Chip>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              Workflow: {request.workflow_thread_id} &middot; Document:{' '}
              {request.document_id}
            </p>
          </div>
          <Typography.Text fontSize="xs" className="text-gray-400">
            {new Date(request.created_at).toLocaleString('en-MY')}
          </Typography.Text>
        </div>

        <div className="mt-3 rounded-md bg-blue-50 p-3">
          <Typography.Text fontSize="s" fontWeight={500}>
            {request.question}
          </Typography.Text>
        </div>

        {lowConfidenceFields.length > 0 && (
          <div className="mt-2">
            <Chip color="red" variant="pill">
              {lowConfidenceFields.length} field(s) below confidence
              threshold
            </Chip>
          </div>
        )}
      </div>

      <div className="px-6 py-4">
        <Typography.H5>Extracted Fields</Typography.H5>
        <div className="mt-3 space-y-3">
          {fields.map((field) => (
            <FieldPreview key={field.name} field={field} />
          ))}
        </div>
      </div>

      <Divider />

      {showCorrection ? (
        <div className="px-6 py-4">
          <CorrectionForm
            fields={fields}
            onSubmit={handleCorrect}
            onCancel={() => setShowCorrection(false)}
          />
        </div>
      ) : (
        <div className="px-6 py-4">
          <Input
            label="Reason (optional for approve, required for reject)"
            value={reason}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setReason(e.target.value)}
            placeholder="e.g. Figures verified against bank statement"
          />

          <div className="mt-4 flex gap-3">
            <Button
              variant="primary"
              onClick={handleApprove}
            >
              Approve
            </Button>
            <Button
              variant="secondary"
              onClick={handleReject}
              disabled={request.status !== 'pending'}
            >
              Reject
            </Button>
            <Button
              variant="tertiary"
              onClick={() => setShowCorrection(true)}
              disabled={request.status !== 'pending'}
            >
              Correct
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
