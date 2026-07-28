import { Typography, Chip } from '@openhands/ui';
import type { WorkflowInstance } from '../../types/dashboard';

type ChipColorType = 'primaryDark' | 'primaryLight' | 'green' | 'red' | 'aqua' | 'gray';

const STATUS_BADGES: Record<
  WorkflowInstance['status'],
  { color: ChipColorType; label: string }
> = {
  pending: { color: 'gray', label: 'Pending' },
  in_progress: { color: 'green', label: 'Active' },
  awaiting_approval: { color: 'primaryDark', label: 'Awaiting' },
  completed: { color: 'green', label: 'Completed' },
  blocked: { color: 'red', label: 'Blocked' },
  failed: { color: 'red', label: 'Failed' },
};

interface WorkflowListProps {
  workflows: WorkflowInstance[];
}

export function WorkflowList({ workflows }: WorkflowListProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417] p-5 shadow-xs">
      <div className="mb-3 flex items-center justify-between">
        <Typography.Text fontWeight={600} fontSize="m" className="text-slate-800 dark:text-white">
          Active Workflows
        </Typography.Text>
        <svg className="h-4 w-4 text-slate-400 dark:text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" d="M7 17L17 7M17 7H7M17 7v10" />
        </svg>
      </div>
      <div className="space-y-2">
        {workflows.length === 0 ? (
          <div className="rounded-lg border border-dashed border-slate-200 dark:border-[#2C2E34] py-8 text-center text-xs text-slate-400 dark:text-slate-500">
            Tiada aliran kerja aktif
          </div>
        ) : (
          workflows.map((wf) => {
            const badge = STATUS_BADGES[wf.status] ?? STATUS_BADGES.pending;
            return (
              <div
                key={wf.id}
                className="flex items-center justify-between rounded-lg border border-slate-100 dark:border-[#222328] px-3 py-2 transition-colors hover:bg-slate-50/50 dark:hover:bg-[#18191C]/50"
              >
                <div className="min-w-0 flex-1 pr-2">
                  <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-200">
                    {wf.applicant || wf.title}
                  </p>
                  <p className="truncate text-xs text-slate-400 dark:text-slate-500">
                    {wf.stage} · {wf.assigned_agent}
                  </p>
                </div>
                <Chip
                  variant="pill"
                  color={badge.color}
                  className="shrink-0 text-xs font-semibold"
                >
                  {badge.label}
                </Chip>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
