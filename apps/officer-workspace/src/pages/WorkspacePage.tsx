import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { AppLayout } from '../components/layout/AppLayout';
import { ChatPanel } from '../components/workspace/ChatPanel';
import { TaskPanel } from '../components/workspace/TaskPanel';
import { startAssessmentFull } from '../services/data';
import { useAssessments } from '../context/AssessmentContext';
import { UI, WORKSPACE } from '../constants';

export function WorkspacePage() {
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { addAssessment } = useAssessments();

  function handleFileAttach() {
    fileInputRef.current?.click();
  }

  async function runAssessment(input: { file: File; sector: string; region: string }) {
    setUploading(true);
    try {
      const res = await startAssessmentFull(input);
      addAssessment({
        thread_id: res.thread_id,
        title: `Loan Assessment — ${res.thread_id.slice(0, 8)}`,
        status: res.status,
        pending_gate: res.pending_gate,
        pending_payload: res.pending_payload,
        stage_log: res.stage_log,
        acted_gate: res.acted_gate,
        created_at: new Date().toISOString(),
      });
      toast.success(`${WORKSPACE.TOAST_ASSESSMENT_STARTED}: ${res.thread_id}`);
    } catch {
      toast.error(WORKSPACE.TOAST_ASSESSMENT_FAILED);
    } finally {
      setUploading(false);
    }
  }

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    await runAssessment({
      file,
      sector: UI.DEFAULT_SECTOR,
      region: UI.DEFAULT_REGION,
    });
    e.target.value = '';
  }

  async function handleSend(text: string): Promise<string> {
    setUploading(true);
    try {
      const dummyPdfContent = '%PDF-1.4\n1 0 obj <</Type /Catalog /Pages 2 0 R>> endobj\n2 0 obj <</Type /Pages /Count 1 /Kids [3 0 R]>> endobj\n3 0 obj <</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources <</Font <</F1 4 0 R>>>> /Contents 5 0 R>> endobj\n4 0 obj <</Type /Font /Subtype /Type1 /BaseFont /Helvetica>> endobj\n5 0 obj <</Length 68>> stream\nBT\n/F1 12 Tf\n100 700 Td\n(Permohonan Pembiayaan Pinjaman Usahawan MARA) Tj\nET\nendstream endobj\nxref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000230 00000 n \n0000000302 00000 n \ntrailer <</Size 6 /Root 1 0 R>>\nstartxref\n420\n%%EOF\n';
      const mockFile = new File([dummyPdfContent], UI.PLACEHOLDER_MOCK_FILE_NAME, { type: 'application/pdf' });
      const res = await startAssessmentFull({
        file: mockFile,
        sector: UI.DEFAULT_SECTOR,
        region: UI.DEFAULT_REGION,
        product_query: text,
      });
      addAssessment({
        thread_id: res.thread_id,
        title: `Loan Assessment — ${res.thread_id.slice(0, 8)}`,
        status: res.status,
        pending_gate: res.pending_gate,
        pending_payload: res.pending_payload,
        stage_log: res.stage_log,
        acted_gate: res.acted_gate,
        created_at: new Date().toISOString(),
      });
      const gateLabel = res.pending_gate
        ? `paused at "${res.pending_gate.replace(/_/g, ' ')}"`
        : 'completed';
      return `Assessment started (${res.thread_id.slice(0, 8)}…). Status: ${res.status}, ${gateLabel}. You can review pending gates in the Review Console.`;
    } catch {
      toast.error(WORKSPACE.TOAST_ASSESSMENT_FAILED);
      return 'Failed to start assessment. The backend may be unavailable.';
    } finally {
      setUploading(false);
    }
  }

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
