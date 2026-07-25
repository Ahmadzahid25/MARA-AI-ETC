import { Chip, Scrollable, Typography } from '@openhands/ui';
import type { Task, TaskStatus } from '../../types/workspace';
import { MOCK_TASKS } from '../../mocks/mock-data';

const STATUS_CONFIG: Record<
  TaskStatus,
  { label: string; color: 'green' | 'primaryDark' | 'gray' | 'red' | 'aqua' }
> = {
  pending: { label: 'Pending', color: 'gray' },
  in_progress: { label: 'In Progress', color: 'aqua' },
  completed: { label: 'Completed', color: 'green' },
  awaiting_approval: { label: 'Awaiting Approval', color: 'primaryDark' },
  blocked: { label: 'Blocked', color: 'red' },
  failed: { label: 'Failed', color: 'red' },
};

export function TaskPanel() {
  const pendingCount = MOCK_TASKS.filter(
    (t) => t.status === 'pending' || t.status === 'in_progress',
  ).length;
  const awaitingCount = MOCK_TASKS.filter(
    (t) => t.status === 'awaiting_approval',
  ).length;

  return (
    <aside className="flex w-72 flex-col border-r bg-white">
      <div className="border-b px-4 py-3">
        <Typography.H5>Tasks</Typography.H5>
        <div className="mt-2 flex gap-2">
          <Chip color="aqua" variant="pill">
            {pendingCount} active
          </Chip>
          {awaitingCount > 0 && (
            <Chip color="primaryDark" variant="pill">
              {awaitingCount} awaiting
            </Chip>
          )}
        </div>
      </div>

      <Scrollable className="flex-1">
        <div className="space-y-1 p-2">
          {MOCK_TASKS.map((task) => (
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
    <div className="cursor-pointer rounded-md px-3 py-2 transition-colors hover:bg-gray-50">
      <div className="flex items-start justify-between gap-2">
        <Typography.Text fontSize="s" fontWeight={500}>
          {task.title}
        </Typography.Text>
        <Chip color={config.color} variant="pill">
          {config.label}
        </Chip>
      </div>
      <div className="mt-1 flex items-center gap-2">
        <Typography.Text fontSize="xxs" className="text-gray-400">
          {task.agent_name}
        </Typography.Text>
        <Typography.Text fontSize="xxs" className="text-gray-300">
          {new Date(task.updated_at).toLocaleTimeString('en-MY', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </Typography.Text>
      </div>
    </div>
  );
}
