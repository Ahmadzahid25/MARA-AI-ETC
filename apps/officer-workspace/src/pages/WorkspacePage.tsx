import { AppLayout } from '../components/layout/AppLayout';
import { ChatPanel } from '../components/workspace/ChatPanel';
import { TaskPanel } from '../components/workspace/TaskPanel';

export function WorkspacePage() {
  return (
    <AppLayout title="Officer Workspace" subtitle="Chat &amp; task view">
      <div className="flex h-full gap-4">
        <TaskPanel />
        <ChatPanel />
      </div>
    </AppLayout>
  );
}
