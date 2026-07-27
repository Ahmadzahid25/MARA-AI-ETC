import { useCallback, useRef, useState } from 'react';
import { toast } from 'sonner';
import { AppLayout } from '../components/layout/AppLayout';
import { ChatPanel } from '../components/workspace/ChatPanel';
import { TaskPanel } from '../components/workspace/TaskPanel';
import { startAssessment } from '../services/data';
import { UI, WORKSPACE } from '../constants';

export function WorkspacePage() {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileAttach = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileSelected = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const result = await startAssessment({
        file,
        sector: UI.DEFAULT_SECTOR,
        region: UI.DEFAULT_REGION,
      });
      toast.success(`${WORKSPACE.TOAST_ASSESSMENT_STARTED}: ${result.threadId}`);
    } catch {
      toast.error(WORKSPACE.TOAST_ASSESSMENT_FAILED);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  }, []);

  const handleSend = useCallback(async (text: string) => {
    if (!text.trim() || uploading) return;

    setUploading(true);
    try {
      const result = await startAssessment({
        file: new File([], UI.PLACEHOLDER_MOCK_FILE_NAME),
        sector: UI.DEFAULT_SECTOR,
        region: UI.DEFAULT_REGION,
      });
      toast.success(`${WORKSPACE.TOAST_ASSESSMENT_STARTED}: ${result.threadId}`);
    } catch {
      toast.error(WORKSPACE.TOAST_ASSESSMENT_FAILED);
    } finally {
      setUploading(false);
    }
  }, [uploading]);

  return (
    <AppLayout title={WORKSPACE.PAGE_TITLE} subtitle={WORKSPACE.PAGE_SUBTITLE}>
      <div className="flex h-full gap-4">
        <TaskPanel />
        <ChatPanel onSend={handleSend} uploading={uploading} onFileAttach={handleFileAttach} />
      </div>
      <input
        ref={fileInputRef}
        type="file"
        accept={UI.ACCEPTED_FILE_TYPES}
        className="hidden"
        onChange={handleFileSelected}
      />
    </AppLayout>
  );
}
