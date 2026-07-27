import { useEffect, useState } from 'react';
import { Chip, Tabs, Typography } from '@openhands/ui';
import { AppLayout } from '../components/layout/AppLayout';
import { ApprovalCard } from '../components/review/ApprovalCard';
import {
  fetchApprovalRequests,
  fetchExtraction,
  submitGateDecision,
  extractGateRole,
  ApiError,
} from '../services/data';
import type { ApprovalRequest } from '../types/approval';
import type { FieldCorrection } from '../types/approval';
import type { ExtractedField } from '../types/documents';

export function ReviewConsolePage() {
  const [requests, setRequests] = useState<ApprovalRequest[]>([]);
  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [loading, setLoading] = useState(true);
  const [gateError, setGateError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setGateError(null);
      setLoadError(null);
      try {
        const reqs = await fetchApprovalRequests();
        setRequests(reqs);
        if (reqs.length > 0) {
          const ext = await fetchExtraction(reqs[0]!.document_id);
          setFields(ext.fields);
        }
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          const role = extractGateRole(err.detail ?? '');
          setGateError(
            role
              ? `This stage requires a ${role} — your role does not have authority at this gate.`
              : err.detail ?? 'You do not have the required role for this gate.',
          );
        } else {
          setLoadError('Review Console data is unavailable. The API endpoint has not been built yet.');
        }
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  async function handleDecision(
    requestId: string,
    action: 'approve' | 'reject' | 'correct',
    reason: string,
    corrections?: FieldCorrection[],
  ) {
    const req = requests.find((r) => r.id === requestId);
    if (!req) return;

    try {
      const result = await submitGateDecision(
        req.workflow_thread_id,
        action,
        reason,
        corrections,
      );

      setRequests((prev) =>
        prev.map((r) =>
          r.id === requestId
            ? {
                ...r,
                status: (
                  action === 'approve' ? 'approved'
                  : action === 'reject' ? 'rejected'
                  : 'corrected'
                ) as ApprovalRequest['status'],
              }
            : r,
        ),
      );

      if (result.actedGate) {
        const reqs = await fetchApprovalRequests();
        setRequests(reqs);
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        const role = extractGateRole(err.detail ?? '');
        setGateError(
          role
            ? `This stage requires a ${role} — your role does not have authority at this gate.`
            : err.detail ?? 'You do not have the required role for this gate.',
        );
      }
    }
  }

  const pending = requests.filter((r) => r.status === 'pending');
  const resolved = requests.filter((r) => r.status !== 'pending');

  return (
    <AppLayout title="Review &amp; Approval Console" subtitle="Human-in-the-loop gates">
      {(gateError || loadError) && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-800/60 dark:bg-amber-950/40">
          <Typography.Text fontSize="s" className="text-amber-800 dark:text-amber-200">
            {gateError ?? loadError}
          </Typography.Text>
        </div>
      )}

      <div className="mb-4">
        <Chip color="primaryDark" variant="pill">
          {loading ? 'Loading...' : `${pending.length} pending`}
        </Chip>
      </div>

      {loading ? (
        <div className="py-12 text-center">
          <Typography.Text fontSize="m" className="text-gray-400">
            Loading approval requests...
          </Typography.Text>
        </div>
      ) : loadError ? (
        <div className="py-12 text-center">
          <Typography.Text fontSize="m" className="text-gray-400">
            {loadError}
          </Typography.Text>
        </div>
      ) : (
        <Tabs>
          <Tabs.Item text={`Pending (${pending.length})`} testId="tab-pending">
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
                    fields={fields}
                    onDecision={handleDecision}
                  />
                ))
              )}
            </div>
          </Tabs.Item>

          <Tabs.Item text={`Resolved (${resolved.length})`} testId="tab-resolved">
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
                    fields={fields}
                    onDecision={handleDecision}
                  />
                ))
              )}
            </div>
          </Tabs.Item>
        </Tabs>
      )}
    </AppLayout>
  );
}
