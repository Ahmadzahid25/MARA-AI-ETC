import { ChatPanel } from '../components/workspace/ChatPanel';
import { TaskPanel } from '../components/workspace/TaskPanel';

export function WorkspacePage() {
  return (
    <div className="flex h-screen flex-col bg-gray-50">
      <header className="flex items-center justify-between border-b bg-white px-6 py-3 shadow-sm">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            MARA AI-ETC
          </h1>
          <p className="text-xs text-gray-500">Officer Workspace</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">Officer</span>
          <button className="rounded-md bg-gray-100 px-3 py-1.5 text-sm text-gray-700 transition-colors hover:bg-gray-200">
            Sign out
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        <TaskPanel />
        <ChatPanel />
      </div>
    </div>
  );
}
