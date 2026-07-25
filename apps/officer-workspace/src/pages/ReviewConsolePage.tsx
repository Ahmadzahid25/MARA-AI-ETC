import { useState } from 'react';
import { Chip, Tabs, Typography } from '@openhands/ui';
import { AppLayout } from '../components/layout/AppLayout';
import { ApprovalCard } from '../components/review/ApprovalCard';
import { MOCK_APPROVAL_REQUESTS, MOCK_EXTRACTION } from '../mocks/mock-data';
import type { FieldCorrection } from '../types/approval';

export function ReviewConsolePage() {
  const [requests, setRequests] = useState(MOCK_APPROVAL_REQUESTS);

  const pending = requests.filter((r) => r.status === 'pending');
  const resolved = requests.filter((r) => r.status !== 'pending');

  function handleDecision(
    requestId: string,
    action: 'approve' | 'reject' | 'correct',
    _reason: string,
    _corrections?: FieldCorrection[],
  ) {
    setRequests((prev) =>
      prev.map((r) =>
        r.id === requestId
          ? {
              ...r,
              status:
                action === 'approve'
                  ? 'approved'
                  : action === 'reject'
                    ? 'rejected'
                    : 'corrected',
            }
          : r,
      ),
    );
  }

  return (
    <AppLayout title="Review &amp; Approval Console" subtitle="Human-in-the-loop gates">
      <div className="mb-4">
        <Chip color="primaryDark" variant="pill">
          {pending.length} pending
        </Chip>
      </div>
      <Tabs>
        <Tabs.Item
          text={`Pending (${pending.length})`}
          testId="tab-pending"
        >
          <div className="mt-4 space-y-6">
            {pending.length === 0 ? (
              <div className="py-12 text-center">
                <Typography.Text fontSize="m" className="text-gray-400">
                  No pending approvals
                </Typography.Text>
              </div>
            ) : (
              pending.map((req) => (
                <ApprovalCard
                  key={req.id}
                  request={req}
                  fields={MOCK_EXTRACTION.fields}
                  onDecision={handleDecision}
                />
              ))
            )}
          </div>
        </Tabs.Item>

        <Tabs.Item
          text={`Resolved (${resolved.length})`}
          testId="tab-resolved"
        >
          <div className="mt-4 space-y-6">
            {resolved.length === 0 ? (
              <div className="py-12 text-center">
                <Typography.Text fontSize="m" className="text-gray-400">
                  No resolved approvals
                </Typography.Text>
              </div>
            ) : (
              resolved.map((req) => (
                <ApprovalCard
                  key={req.id}
                  request={req}
                  fields={MOCK_EXTRACTION.fields}
                  onDecision={handleDecision}
                />
              ))
            )}
          </div>
        </Tabs.Item>
      </Tabs>
    </AppLayout>
  );
}
