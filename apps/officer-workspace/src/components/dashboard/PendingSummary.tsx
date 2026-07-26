import { Typography, Chip } from '@openhands/ui';
import type { PendingApprovalSummary, RiskFlag } from '../../types/dashboard';

type ChipColorType = 'primaryDark' | 'primaryLight' | 'green' | 'red' | 'aqua' | 'gray';

const SEVERITY_COLORS: Record<string, ChipColorType> = {
  low: 'gray',
  medium: 'primaryDark',
  high: 'red',
  critical: 'red',
};

interface PendingSummaryProps {
  approvals: PendingApprovalSummary[];
  riskFlags: RiskFlag[];
}

export function PendingSummary({ approvals, riskFlags }: PendingSummaryProps) {
  return (
    <div className="space-y-4">
      {/* Pending Summary Box */}
      <div className="rounded-2xl border border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417] p-5 shadow-xs">
        <div className="mb-3">
          <Typography.Text fontWeight={600} fontSize="m" className="text-slate-800 dark:text-white">
            Pending Summary
          </Typography.Text>
        </div>
        <div className="space-y-2.5">
          {approvals.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 dark:border-[#2C2E34] py-8 text-center text-xs text-slate-400 dark:text-slate-500">
              Tiada kelulusan tertunda
            </div>
          ) : (
            approvals.map((a) => (
              <div key={a.id} className="rounded-lg border border-slate-100 dark:border-[#222328] px-3.5 py-2.5 transition-colors hover:bg-slate-50/50 dark:hover:bg-[#18191C]/50">
                <p className="text-sm font-medium text-slate-800 dark:text-slate-200">
                  {a.workflow_title}
                </p>
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">{a.question}</p>
                <div className="mt-2 flex items-center justify-between text-xs text-slate-400 dark:text-slate-500">
                  <span>{a.agent_name} · {a.assigned_to}</span>
                  <span className="font-semibold text-amber-600 dark:text-amber-400">
                    {a.age_hours.toFixed(1)}h tertunda
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Risk Flags Box */}
      <div className="rounded-2xl border border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417] p-5 shadow-xs">
        <div className="mb-3">
          <Typography.Text fontWeight={600} fontSize="m" className="text-slate-800 dark:text-white">
            Risk Flags
          </Typography.Text>
        </div>
        <div className="space-y-2">
          {riskFlags.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-200 dark:border-[#2C2E34] py-8 text-center text-xs text-slate-400 dark:text-slate-500">
              Tiada amaran risiko dikesan
            </div>
          ) : (
            riskFlags.map((rf) => {
              const badgeColor = SEVERITY_COLORS[rf.severity] ?? 'gray';
              return (
                <div key={rf.id} className="flex items-start justify-between gap-3 rounded-lg border border-slate-100 dark:border-[#222328] px-3.5 py-2.5 transition-colors hover:bg-slate-50/50 dark:hover:bg-[#18191C]/50">
                  <div className="flex items-start gap-2.5 min-w-0 flex-1">
                    <svg className="mt-0.5 h-4 w-4 shrink-0 text-amber-500 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm text-slate-700 dark:text-slate-200 font-medium leading-snug">{rf.description}</p>
                      <p className="mt-0.5 text-xs text-slate-400 dark:text-slate-500">
                        {rf.agent_name} · Workflow {rf.workflow_id}
                      </p>
                    </div>
                  </div>
                  <Chip
                    variant="pill"
                    color={badgeColor}
                    className="shrink-0 text-xs font-semibold uppercase"
                  >
                    {rf.severity}
                  </Chip>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

