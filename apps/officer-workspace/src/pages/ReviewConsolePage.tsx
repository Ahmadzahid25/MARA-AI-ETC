import { useState } from 'react';
import { Button, Chip, Input, Tabs, Typography } from '@openhands/ui';
import { AppLayout } from '../components/layout/AppLayout';
import { GateRenderer } from '../components/review/GateRenderer';
import { useAssessments } from '../context/AssessmentContext';
import { submitGateDecision, extractGateRole, ApiError } from '../services/data';
import type { PendingGate } from '../services/api';
import type { FieldCorrection } from '../types/approval';

export function ReviewConsolePage() {
  const { assessments, updateAssessment } = useAssessments();
  const [activeAssessmentId, setActiveAssessmentId] = useState<string | null>(null);

  const activeAssessment = activeAssessmentId
    ? assessments.find((a) => a.thread_id === activeAssessmentId)
    : null;

  const pendingAssessments = assessments.filter((a) => a.status === 'pending_approval');
  const completedAssessments = assessments.filter((a) => a.status === 'completed');

  if (assessments.length === 0) {
    return (
      <AppLayout title="Review &amp; Approval Console" subtitle="Human-in-the-loop gates">
        <div className="py-20 text-center">
          <Typography.Text fontSize="m" className="text-gray-400">
            No assessments yet. Start one from the Workspace.
          </Typography.Text>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Review &amp; Approval Console" subtitle="Human-in-the-loop gates">
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
  const [corrections, setCorrections] = useState<FieldCorrection[]>([]);

  async function handleAction(action: 'approve' | 'reject' | 'correct') {
    if (submitting) return;
    setSubmitting(true);
    setGateError(null);

    try {
      const res = await submitGateDecision(
        assessment.thread_id,
        action,
        reason,
        corrections,
      );
      onUpdated({
        status: res.status,
        pending_gate: res.pending_gate,
        pending_payload: res.pending_payload,
        stage_log: res.stage_log,
        acted_gate: res.acted_gate,
      });
      setReason('');
      setCorrections([]);
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
          <Typography.H5 className="mb-3 text-slate-900 dark:text-white">Current Gate</Typography.H5>
          {assessment.pending_gate ? (
            <GateRenderer gate={assessment.pending_gate} payload={assessment.pending_payload} />
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
              <div className="space-y-3">
                <Typography.Text fontSize="s" className="text-slate-500 dark:text-slate-400">
                  Enter corrected values for fields that need changes.
                </Typography.Text>
                <Input
                  label="Correction reason"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  placeholder="Why are these corrections needed?"
                />
                <div className="flex gap-3">
                  <Button variant="primary" onClick={() => handleAction('correct')} disabled={submitting}>
                    {submitting ? 'Submitting...' : 'Submit Correction'}
                  </Button>
                  <Button variant="secondary" onClick={() => setShowCorrect(false)}>
                    Cancel
                  </Button>
                </div>
              </div>
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
