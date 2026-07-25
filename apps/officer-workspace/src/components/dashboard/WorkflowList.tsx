import { Typography } from '@openhands/ui';
import type { WorkflowInstance } from '../../types/dashboard';

const STATUS_BADGES: Record<
  WorkflowInstance['status'],
  { bg: string; text: string; label: string }
> = {
  pending: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'Pending' },
  in_progress: {
    bg: 'bg-blue-100',
    text: 'text-blue-700',
    label: 'In Progress',
  },
  awaiting_approval: {
    bg: 'bg-amber-100',
    text: 'text-amber-700',
    label: 'Awaiting Approval',
  },
  completed: {
    bg: 'bg-green-100',
    text: 'text-green-700',
    label: 'Completed',
  },
  blocked: { bg: 'bg-red-100', text: 'text-red-700', label: 'Blocked' },
  failed: { bg: 'bg-red-100', text: 'text-red-700', label: 'Failed' },
};

interface WorkflowListProps {
  workflows: WorkflowInstance[];
}

export function WorkflowList({ workflows }: WorkflowListProps) {
  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="border-b px-4 py-3">
          <Typography.Text fontWeight={600} fontSize="m">
          Active Workflows
        </Typography.Text>
      </div>
      <div className="divide-y">
        {workflows.length === 0 ? (
          <div className="px-4 py-8 text-center text-gray-400">
            No active workflows
          </div>
        ) : (
          workflows.map((wf) => {
            const badge = STATUS_BADGES[wf.status] ?? STATUS_BADGES.pending;
            return (
              <div
                key={wf.id}
                className="flex items-center justify-between px-4 py-3"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-gray-900">
                    {wf.title}
                  </p>
                  <p className="text-xs text-gray-500">
                    {wf.applicant} · {wf.stage} · {wf.assigned_agent}
                  </p>
                </div>
                <span
                  className={`ml-3 shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${badge.bg} ${badge.text}`}
                >
                  {badge.label}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
