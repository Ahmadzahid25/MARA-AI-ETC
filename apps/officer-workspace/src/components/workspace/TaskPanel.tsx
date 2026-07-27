import { useEffect, useState } from 'react';
import { Chip, Scrollable, Typography } from '@openhands/ui';
import type { Task, TaskStatus } from '../../types/workspace';
import { fetchTasks } from '../../services/data';
import { UI, WORKSPACE } from '../../constants';

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; color: 'green' | 'primaryDark' | 'gray' | 'red' | 'aqua'; bg: string }
> = {
  pending: { label: 'Pending', color: 'gray', bg: 'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800/80 dark:text-slate-300 dark:border-slate-700/60' },
  in_progress: { label: 'In Progress', color: 'aqua', bg: 'bg-cyan-50 text-cyan-700 border-cyan-200 dark:bg-cyan-950/80 dark:text-cyan-300 dark:border-cyan-800/60' },
  completed: { label: 'Completed', color: 'green', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/80 dark:text-emerald-300 dark:border-emerald-800/60' },
  awaiting_approval: { label: 'Awaiting Approval', color: 'primaryDark', bg: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/80 dark:text-amber-300 dark:border-amber-800/60' },
  blocked: { label: 'Blocked', color: 'red', bg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/80 dark:text-rose-300 dark:border-rose-800/60' },
  failed: { label: 'Failed', color: 'red', bg: 'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/80 dark:text-rose-300 dark:border-rose-800/60' },
};

export function TaskPanel() {
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    fetchTasks().then(setTasks);
  }, []);

  const pendingCount = tasks.filter(
    (t) => t.status === 'pending' || t.status === 'in_progress',
  ).length;
  const awaitingCount = tasks.filter(
    (t) => t.status === 'awaiting_approval',
  ).length;

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417]">
      <div className="border-b border-slate-100 bg-slate-50/50 dark:border-[#222328] dark:bg-[#18191C]/50 px-4 py-3.5">
        <div className="flex items-center justify-between">
          <Typography.H5 className="font-bold text-slate-900 dark:text-white">{WORKSPACE.TASK_HEADING}</Typography.H5>
          <span className="rounded-full bg-slate-200/60 dark:bg-[#222328] px-2 py-0.5 text-xs font-semibold text-slate-600 dark:text-slate-300">
            {tasks.length}
          </span>
        </div>
        <div className="mt-2.5 flex flex-wrap gap-1.5">
          <Chip color="aqua" variant="pill" className="border-cyan-200 bg-cyan-50 text-cyan-700 dark:border-cyan-800/60 dark:bg-cyan-950/80 text-xs font-semibold dark:text-cyan-300">
            {pendingCount} {WORKSPACE.CHIP_ACTIVE_LABEL}
          </Chip>
          {awaitingCount > 0 && (
            <Chip color="primaryDark" variant="pill" className="border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800/60 dark:bg-amber-950/80 text-xs font-semibold dark:text-amber-300">
              {awaitingCount} {WORKSPACE.CHIP_AWAITING_LABEL}
            </Chip>
          )}
        </div>
      </div>

      <Scrollable className="flex-1">
        <div className="space-y-1.5 p-2.5">
          {tasks.map((task) => (
            <TaskItem key={task.id} task={task} />
          ))}
        </div>
      </Scrollable>
    </aside>
  );
}

function TaskItem({ task }: { task: Task }) {
  const config = STATUS_CONFIG[task.status];

  return (
    <div className="cursor-pointer rounded-xl border border-transparent p-3 transition-all hover:border-slate-200 hover:bg-slate-50 hover:shadow-sm dark:hover:border-[#2C2E34] dark:hover:bg-[#18191C] dark:hover:shadow-lg">
      <div className="mb-2 flex items-center justify-between gap-1">
        <Chip color={config.color} variant="pill" className={`shrink-0 px-2 py-0.5 ${WORKSPACE.FONT_XS_11} font-semibold ${config.bg}`}>
          {config.label}
        </Chip>
        <span className={`${WORKSPACE.FONT_XS_11} font-medium text-slate-400 dark:text-slate-500`}>
          {new Date(task.updated_at).toLocaleTimeString(UI.LOCALE, UI.DATE_FORMAT_OPTIONS)}
        </span>
      </div>
      <Typography.Text fontSize="s" className="block font-semibold leading-snug text-slate-800 dark:text-slate-200 line-clamp-2">
        {task.title}
      </Typography.Text>
      <div className="mt-2 flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span className="flex items-center gap-1.5 truncate">
          <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500"></span>
          <span className="truncate font-medium">{task.agent_name}</span>
        </span>
      </div>
    </div>
  );
}
