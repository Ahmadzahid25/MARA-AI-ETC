import { Typography } from '@openhands/ui';
import type { PendingApprovalSummary, RiskFlag } from '../../types/dashboard';

const SEVERITY_BADGES: Record<string, string> = {
  low: 'bg-gray-100 text-gray-600',
  medium: 'bg-amber-100 text-amber-700',
  high: 'bg-orange-100 text-orange-700',
  critical: 'bg-red-100 text-red-700',
};

interface PendingSummaryProps {
  approvals: PendingApprovalSummary[];
  riskFlags: RiskFlag[];
}

export function PendingSummary({ approvals, riskFlags }: PendingSummaryProps) {
  return (
    <div className="space-y-4">
      <div className="rounded-lg border bg-white shadow-sm">
        <div className="border-b px-4 py-3">
          <Typography.Text fontWeight={600} fontSize="m">
            Pending Approvals
          </Typography.Text>
        </div>
        <div className="divide-y">
          {approvals.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-400">
              No pending approvals
            </div>
          ) : (
            approvals.map((a) => (
              <div key={a.id} className="px-4 py-3">
                <p className="text-sm font-medium text-gray-900">
                  {a.workflow_title}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">{a.question}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-gray-400">
                  <span>{a.agent_name}</span>
                  <span>·</span>
                  <span>{a.age_hours.toFixed(1)}h old</span>
                  <span>·</span>
                  <span>{a.assigned_to}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="rounded-lg border bg-white shadow-sm">
        <div className="border-b px-4 py-3">
          <Typography.Text fontWeight={600} fontSize="m">
            Risk Flags
          </Typography.Text>
        </div>
        <div className="divide-y">
          {riskFlags.length === 0 ? (
            <div className="px-4 py-8 text-center text-gray-400">
              No risk flags
            </div>
          ) : (
            riskFlags.map((rf) => {
              const badge = SEVERITY_BADGES[rf.severity] ?? SEVERITY_BADGES.low;
              return (
                <div key={rf.id} className="px-4 py-3">
                  <div className="flex items-start justify-between">
                    <p className="text-sm text-gray-900">{rf.description}</p>
                    <span
                      className={`ml-2 shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${badge}`}
                    >
                      {rf.severity}
                    </span>
                  </div>
                  <p className="mt-0.5 text-xs text-gray-400">
                    {rf.agent_name} · Workflow {rf.workflow_id}
                  </p>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
