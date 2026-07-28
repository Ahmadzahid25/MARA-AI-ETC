import { Chip, Scrollable, Typography } from '@openhands/ui';
import { useAssessments } from '../../context/AssessmentContext';
import { WORKSPACE } from '../../constants';
import type { StageLogEntry } from '../../services/api';

const STAGE_STATUS_CONFIG: Record<
  string,
  { label: string; color: 'green' | 'primaryDark' | 'gray'; dot: string }
> = {
  completed: { label: 'Done', color: 'green', dot: 'bg-emerald-500' },
  in_progress: { label: 'Running', color: 'primaryDark', dot: 'bg-cyan-500 animate-pulse' },
  pending: { label: 'Pending', color: 'gray', dot: 'bg-slate-300 dark:bg-slate-600' },
};

const STAGE_STATUS_DEFAULT = { label: 'Pending', color: 'gray' as const, dot: 'bg-slate-300 dark:bg-slate-600' };

function stageLabel(stage: string | undefined | null): string {
  if (!stage) return 'Stage';
  return stage
    .replace(/^extract_/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function StageRow({ entry }: { entry: StageLogEntry | string | any }) {
  const stageName = typeof entry === 'string' ? entry : entry?.stage;
  const statusStr = typeof entry === 'string' ? 'completed' : (entry?.status ?? 'completed');
  const agentName = typeof entry === 'string' ? '' : entry?.agent;
  const completedAt = typeof entry === 'string' ? null : entry?.completed_at;

  const config = STAGE_STATUS_CONFIG[statusStr] ?? STAGE_STATUS_DEFAULT;

  return (
    <div className="flex items-start gap-3 px-3 py-2">
      <div className="flex shrink-0 flex-col items-center pt-1.5">
        <span className={`h-2 w-2 rounded-full ${config.dot}`} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Typography.Text fontSize="s" fontWeight={600} className="text-slate-800 dark:text-slate-200">
            {stageLabel(stageName)}
          </Typography.Text>
          <Chip color={config.color} variant="pill">
            {config.label}
          </Chip>
        </div>
        {agentName && (
          <Typography.Text fontSize="xxs" className="text-slate-400 dark:text-slate-500">
            {agentName}
          </Typography.Text>
        )}
        {completedAt && (
          <Typography.Text fontSize="xxs" className="text-slate-400 dark:text-slate-500">
            {new Date(completedAt).toLocaleTimeString()}
          </Typography.Text>
        )}
      </div>
    </div>
  );
}

export function TaskPanel() {
  const { assessments } = useAssessments();
  const latest = assessments[0];
  const stages = latest?.stage_log ?? [];
  const stageCount = stages.length;
  const activeCount = stages.filter((s) => s.status === 'in_progress').length;
  const awaitingGate = latest?.pending_gate ?? null;

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417]">
      <div className="border-b border-slate-100 bg-slate-50/50 px-4 py-3.5 dark:border-[#222328] dark:bg-[#18191C]/50">
        <div className="flex items-center justify-between">
          <Typography.H5 className="font-bold text-slate-900 dark:text-white">
            {WORKSPACE.TASK_HEADING}
          </Typography.H5>
          {stageCount > 0 && (
            <span className="rounded-full bg-slate-200/60 px-2 py-0.5 text-xs font-semibold text-slate-600 dark:bg-[#222328] dark:text-slate-300">
              {stageCount}
            </span>
          )}
        </div>
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          {activeCount > 0 && (
            <Chip color="aqua" variant="pill" className="border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-800/60 dark:bg-cyan-950/80 text-xs font-semibold dark:text-cyan-300">
              {activeCount} {WORKSPACE.CHIP_ACTIVE_LABEL}
            </Chip>
          )}
          {awaitingGate && (
            <Chip color="primaryDark" variant="pill" className="border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/60 dark:bg-amber-950/80 text-xs font-semibold dark:text-amber-300">
              Awaiting {awaitingGate.replace(/_/g, ' ')}
            </Chip>
          )}
        </div>
      </div>

      <Scrollable className="flex-1">
        {stageCount > 0 ? (
          <div className="divide-y divide-slate-100 dark:divide-[#222328]">
            {stages.map((entry, i) => (
              <StageRow key={`${entry.stage}-${i}`} entry={entry} />
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center px-4 py-12 text-center">
            <Typography.Text fontSize="s" className="text-slate-400 dark:text-slate-500">
              Start an assessment from the chat below to see agent progress here.
            </Typography.Text>
          </div>
        )}
      </Scrollable>
    </aside>
  );
}
