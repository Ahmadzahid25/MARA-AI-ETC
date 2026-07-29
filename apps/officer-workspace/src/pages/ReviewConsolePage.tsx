import { useEffect, useState } from 'react';
import { Button, Chip, Input, Tabs, Typography } from '@openhands/ui';
import { AppLayout } from '../components/layout/AppLayout';
import { GateRenderer } from '../components/review/GateRenderer';
import { CorrectionForm } from '../components/review/CorrectionForm';
import { useAssessments } from '../context/AssessmentContext';
import {
  submitGateDecision,
  extractGateRole,
  ApiError,
  fetchOfficerQueueItems,
  submitOfficerDecision,
} from '../services/data';
import {
  type PendingGate,
  type V1ApplicationStatus,
  type V1OfficerDecisionAction,
  type V1OfficerQueueItem,
} from '../services/api';
import type { FieldCorrection } from '../types/approval';
import type { ExtractedField } from '../types/documents';

export function ReviewConsolePage() {
  const { assessments, updateAssessment } = useAssessments();
  const [queueItems, setQueueItems] = useState<V1OfficerQueueItem[]>([]);
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState<string | null>(null);
  const [queueActionLoading, setQueueActionLoading] = useState<string | null>(null);
  const [activeAssessmentId, setActiveAssessmentId] = useState<string | null>(null);

  useEffect(() => {
    async function loadQueue() {
      setQueueLoading(true);
      setQueueError(null);
      try {
        const queue = await fetchOfficerQueueItems();
        setQueueItems(queue);
      } catch (err) {
        if (err instanceof ApiError && err.status === 403) {
          setQueueError('Queue ini memerlukan peranan Officer/Admin.');
        } else {
          setQueueError('Gagal memuat queue permohonan pegawai.');
        }
      } finally {
        setQueueLoading(false);
      }
    }

    loadQueue();
  }, []);

  const activeAssessment = activeAssessmentId
    ? assessments.find((a) => a.thread_id === activeAssessmentId)
    : null;

  const pendingAssessments = assessments.filter((a) => a.status === 'pending_approval');
  const completedAssessments = assessments.filter((a) => a.status === 'completed');

  async function handleQueueDecision(
    applicationId: string,
    action: V1OfficerDecisionAction,
  ) {
    if (queueActionLoading) return;
    setQueueActionLoading(`${applicationId}:${action}`);
    try {
      await submitOfficerDecision(
        applicationId,
        action,
        action === 'approve'
          ? 'Approved by officer via workspace queue'
          : action === 'reject'
            ? 'Rejected by officer via workspace queue'
            : 'Additional information required by officer',
      );
      const queue = await fetchOfficerQueueItems();
      setQueueItems(queue);
    } catch (err) {
      if (err instanceof ApiError) {
        setQueueError(err.detail ?? err.message);
      } else {
        setQueueError('Keputusan gagal dihantar. Sila cuba lagi.');
      }
    } finally {
      setQueueActionLoading(null);
    }
  }

  function queueStatusChip(status: V1ApplicationStatus): {
    color: 'gray' | 'green' | 'red' | 'primaryDark';

    label: string;
  } {
    if (status === 'PROCESSING') return { color: 'primaryDark', label: 'Processing' };
    if (status === 'UNDER_REVIEW') return { color: 'primaryDark', label: 'Under Review' };
    if (status === 'APPROVED') return { color: 'green', label: 'Approved' };
    if (status === 'REJECTED') return { color: 'red', label: 'Rejected' };
    if (status === 'NEEDS_INFO') return { color: 'red', label: 'Needs Info' };
    return { color: 'gray', label: status.replace(/_/g, ' ') };
  }

  if (assessments.length === 0) {
    return (
      <AppLayout title="Review &amp; Approval Console" subtitle="Human-in-the-loop gates">
        <div className="space-y-6 py-4">
          <VerticalSliceQueuePanel
            queueItems={queueItems}
            queueLoading={queueLoading}
            queueError={queueError}
            queueActionLoading={queueActionLoading}
            onDecision={handleQueueDecision}
          />
          <div className="py-10 text-center">
            <Typography.Text fontSize="m" className="text-gray-400">
              No legacy assessments yet. Start one from the Workspace.
            </Typography.Text>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Review &amp; Approval Console" subtitle="Human-in-the-loop gates">
      <div className="mb-6">
        <VerticalSliceQueuePanel
          queueItems={queueItems}
          queueLoading={queueLoading}
          queueError={queueError}
          queueActionLoading={queueActionLoading}
          onDecision={handleQueueDecision}
        />
      </div>

      <div className="mb-4 flex items-center gap-2">
        <Chip color="primaryDark" variant="pill">
          {pendingAssessments.length} pending
        </Chip>
        <Chip color="green" variant="pill">
          {completedAssessments.length} completed
        </Chip>
      </div>

      {activeAssessment ? (
        <AssessmentDetail
          assessment={activeAssessment}
          onBack={() => setActiveAssessmentId(null)}
          onUpdated={(patch) => updateAssessment(activeAssessment.thread_id, patch)}
        />
      ) : (
        <Tabs>
          <Tabs.Item text={`Pending (${pendingAssessments.length})`} testId="tab-pending">
            <div className="mt-4 space-y-4">
              {pendingAssessments.map((a) => (
                <AssessmentCard
                  key={a.thread_id}
                  assessment={a}
                  onClick={() => setActiveAssessmentId(a.thread_id)}
                />
              ))}
            </div>
          </Tabs.Item>
          <Tabs.Item text={`Completed (${completedAssessments.length})`} testId="tab-completed">
            <div className="mt-4 space-y-4">
              {completedAssessments.map((a) => (
                <AssessmentCard
                  key={a.thread_id}
                  assessment={a}
                  onClick={() => setActiveAssessmentId(a.thread_id)}
                />
              ))}
            </div>
          </Tabs.Item>
        </Tabs>
      )}
    </AppLayout>
  );

  function VerticalSliceQueuePanel({
    queueItems,
    queueLoading,
    queueError,
    queueActionLoading,
    onDecision,
  }: {
    queueItems: V1OfficerQueueItem[];
    queueLoading: boolean;
    queueError: string | null;
    queueActionLoading: string | null;
    onDecision: (applicationId: string, action: V1OfficerDecisionAction) => Promise<void>;
  }) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-[#222328] dark:bg-[#131417]">
        <div className="mb-3 flex items-center justify-between">
          <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
            Vertical Slice Officer Queue
          </Typography.Text>
          <Chip color="primaryDark" variant="pill">
            {queueItems.length} items
          </Chip>
        </div>

        {queueLoading && (
          <Typography.Text fontSize="xs" className="text-slate-500 dark:text-slate-400">
            Loading officer queue...
          </Typography.Text>
        )}

        {!queueLoading && queueError && (
          <Typography.Text fontSize="xs" className="text-amber-600 dark:text-amber-400">
            {queueError}
          </Typography.Text>
        )}

        {!queueLoading && !queueError && queueItems.length === 0 && (
          <Typography.Text fontSize="xs" className="text-slate-500 dark:text-slate-400">
            Tiada permohonan dalam queue buat masa ini.
          </Typography.Text>
        )}

        {!queueLoading && !queueError && queueItems.length > 0 && (
          <div className="space-y-3">
            {queueItems.map((item) => {
              const statusMeta = queueStatusChip(item.status);
              const approveKey = `${item.application_id}:approve`;
              const rejectKey = `${item.application_id}:reject`;
              const requestInfoKey = `${item.application_id}:request_more_info`;
              return (
                <div
                  key={item.application_id}
                  className="rounded-md border border-slate-100 p-3 dark:border-[#222328]"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
                        {item.applicant_name}
                      </Typography.Text>
                      <Typography.Text fontSize="xs" className="block text-slate-500 dark:text-slate-400">
                        {item.scheme} · RM {item.amount_requested.toLocaleString('en-MY')}
                      </Typography.Text>
                    </div>
                    <Chip color={statusMeta.color} variant="pill">
                      {statusMeta.label}
                    </Chip>
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      variant="primary"
                      disabled={queueActionLoading !== null}
                      onClick={() => onDecision(item.application_id, 'approve')}
                    >
                      {queueActionLoading === approveKey ? 'Submitting...' : 'Approve'}
                    </Button>
                    <Button
                      variant="secondary"
                      disabled={queueActionLoading !== null}
                      onClick={() => onDecision(item.application_id, 'reject')}
                    >
                      {queueActionLoading === rejectKey ? 'Submitting...' : 'Reject'}
                    </Button>
                    <Button
                      variant="tertiary"
                      disabled={queueActionLoading !== null}
                      onClick={() => onDecision(item.application_id, 'request_more_info')}
                    >
                      {queueActionLoading === requestInfoKey ? 'Submitting...' : 'Request Info'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }
}

function AssessmentCard({
  assessment,
  onClick,
}: {
  assessment: { thread_id: string; title: string; status: string; pending_gate: string | null };
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full cursor-pointer rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm transition-all hover:border-indigo-300 hover:shadow-md dark:border-[#222328] dark:bg-[#131417] dark:hover:border-indigo-700"
    >
      <div className="flex items-center justify-between">
        <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
          {assessment.title}
        </Typography.Text>
        <Chip
          color={assessment.status === 'pending_approval' ? 'primaryDark' : 'green'}
          variant="pill"
        >
          {assessment.status === 'pending_approval' ? 'Pending' : 'Completed'}
        </Chip>
      </div>
      {assessment.pending_gate && (
        <Typography.Text fontSize="xs" className="mt-1 text-slate-500 dark:text-slate-400">
          At gate: {assessment.pending_gate.replace(/_/g, ' ')}
        </Typography.Text>
      )}
    </button>
  );
}

const GATE_QUESTIONS: Record<string, string> = {
  confirm_extraction: 'Confirm that the extracted document fields are accurate. Verify values against the source document.',
  compliance_acknowledgment: 'Acknowledge the compliance check results below. Are there any policy violations that need attention?',
  financial_sign_off: 'Review the financial assessment. Do the figures and metrics look correct?',
  risk_review: 'Review the risk rating and flags. Is the risk assessment appropriate for this application?',
  recommendation_approval: 'Review the recommendation. Do you approve the suggested decision?',
  publish_approval: 'Review the generated documents. Are they ready to be published to the applicant?',
};

function extractFieldsFromPayload(payload: Record<string, unknown> | null): ExtractedField[] | null {
  if (!payload?.fields || !Array.isArray(payload.fields)) return null;
  return payload.fields as ExtractedField[];
}

function AssessmentDetail({
  assessment,
  onBack,
  onUpdated,
}: {
  assessment: {
    thread_id: string;
    title: string;
    status: string;
    pending_gate: PendingGate | null;
    pending_payload: Record<string, unknown> | null;
    stage_log: Array<{ stage: string; status: string; agent: string; started_at: string; completed_at: string | null }>;
  };
  onBack: () => void;
  onUpdated: (patch: Record<string, unknown>) => void;
}) {
  const [submitting, setSubmitting] = useState(false);
  const [gateError, setGateError] = useState<string | null>(null);
  const [reason, setReason] = useState('');
  const [showCorrect, setShowCorrect] = useState(false);
  async function handleAction(
    action: 'approve' | 'reject' | 'correct',
    fieldCorrections?: FieldCorrection[],
  ) {
    if (submitting) return;
    setSubmitting(true);
    setGateError(null);

    try {
      const res = await submitGateDecision(
        assessment.thread_id,
        action,
        reason,
        fieldCorrections,
      );
      onUpdated({
        status: res.status,
        pending_gate: res.pending_gate,
        pending_payload: res.pending_payload,
        stage_log: res.stage_log,
        acted_gate: res.acted_gate,
      });
      setReason('');
      setShowCorrect(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        const role = extractGateRole(err.detail ?? '');
        setGateError(
          role
            ? `This stage requires a ${role} — your role does not have authority at this gate.`
            : err.detail ?? 'You do not have the required role for this gate.',
        );
      } else if (err instanceof ApiError && err.status === 503) {
        setGateError('OCR/document-classifier engine is not available yet. Expected until M4 integration is complete.');
      } else {
        setGateError('Failed to submit decision. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  const isPending = assessment.status === 'pending_approval';

  return (
    <div>
      <button
        type="button"
        onClick={onBack}
        className="mb-4 cursor-pointer text-sm font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400"
      >
        &larr; Back to assessments
      </button>

      <div className="rounded-lg border border-gray-200 bg-white shadow-sm dark:border-[#222328] dark:bg-[#131417]">
        <div className="border-b border-gray-100 px-6 py-4 dark:border-[#222328]">
          <div className="flex items-center justify-between">
            <Typography.H4 className="text-slate-900 dark:text-white">
              {assessment.title}
            </Typography.H4>
            <div className="flex items-center gap-2">
              {assessment.pending_gate && (
                <Chip color="primaryDark" variant="pill">
                  {assessment.pending_gate.replace(/_/g, ' ')}
                </Chip>
              )}
              <Chip color={isPending ? 'primaryDark' : 'green'} variant="corner">
                {isPending ? 'Pending Approval' : 'Completed'}
              </Chip>
            </div>
          </div>
          <Typography.Text fontSize="xs" className="mt-1 text-slate-400 dark:text-slate-500">
            Thread: {assessment.thread_id}
          </Typography.Text>
        </div>

        {gateError && (
          <div className="mx-6 mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 dark:border-amber-800/60 dark:bg-amber-950/40">
            <Typography.Text fontSize="s" className="text-amber-800 dark:text-amber-200">
              {gateError}
            </Typography.Text>
          </div>
        )}

        <div className="px-6 py-4">
          <Typography.H5 className="mb-1 text-slate-900 dark:text-white">Current Gate</Typography.H5>
          {assessment.pending_gate ? (
            <>
              <Typography.Text fontSize="xs" className="mb-4 block text-slate-500 dark:text-slate-400">
                {GATE_QUESTIONS[assessment.pending_gate] ?? 'Review the information below and make a decision.'}
              </Typography.Text>
              <GateRenderer gate={assessment.pending_gate} payload={assessment.pending_payload} />
            </>
          ) : (
            <Typography.Text fontSize="s" className="text-slate-400">
              No pending gate — assessment is complete.
            </Typography.Text>
          )}
        </div>

        {assessment.stage_log.length > 0 && (
          <>
            <div className="border-t border-gray-100 px-6 py-4 dark:border-[#222328]">
              <Typography.H5 className="mb-3 text-slate-900 dark:text-white">Stage Log</Typography.H5>
              <div className="space-y-2">
                {assessment.stage_log.map((entry, i) => (
                  <div key={i} className="flex items-center justify-between rounded-md bg-slate-50 p-2 text-sm dark:bg-[#18191C]">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-slate-700 dark:text-slate-300">{entry.stage}</span>
                      <Chip
                        color={entry.status === 'completed' ? 'green' : entry.status === 'in_progress' ? 'primaryDark' : 'gray'}
                        variant="pill"
                      >
                        {entry.status}
                      </Chip>
                    </div>
                    <span className="text-xs text-slate-400 dark:text-slate-500">{entry.agent}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}

        {isPending && (
          <div className="border-t border-gray-100 px-6 py-4 dark:border-[#222328]">
            <Typography.H5 className="mb-3 text-slate-900 dark:text-white">Decision</Typography.H5>

            {showCorrect ? (
              assessment.pending_gate === 'confirm_extraction' ? (
                <CorrectionForm
                  fields={extractFieldsFromPayload(assessment.pending_payload) ?? []}
                  onSubmit={(fieldCorrections) => {
                    setReason(fieldCorrections.map((c) => c.reason).filter(Boolean).join('; ') || 'Field corrections applied');
                    handleAction('correct', fieldCorrections);
                  }}
                  onCancel={() => setShowCorrect(false)}
                />
              ) : (
                <div className="space-y-3">
                  <Typography.Text fontSize="s" className="text-slate-500 dark:text-slate-400">
                    Describe what needs to be corrected and why. This will trigger a re-run of the current stage.
                  </Typography.Text>
                  <Input
                    label="Correction reason"
                    value={reason}
                    onChange={(e) => setReason(e.target.value)}
                    placeholder="What needs to be corrected and why?"
                  />
                  <div className="flex gap-3">
                    <Button variant="primary" onClick={() => handleAction('correct')} disabled={submitting}>
                      {submitting ? 'Submitting...' : 'Submit Correction'}
                    </Button>
                    <Button variant="secondary" onClick={() => { setShowCorrect(false); setReason(''); }}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )
            ) : (
              <div className="space-y-3">
                <Input
                  label="Reason (optional)"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="e.g. Figures verified against source documents"
                />
                <div className="flex gap-3">
                  <Button variant="primary" onClick={() => handleAction('approve')} disabled={submitting}>
                    {submitting ? 'Submitting...' : 'Approve'}
                  </Button>
                  <Button variant="secondary" onClick={() => handleAction('reject')} disabled={submitting}>
                    Reject
                  </Button>
                  <Button variant="tertiary" onClick={() => setShowCorrect(true)} disabled={submitting}>
                    Correct
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
