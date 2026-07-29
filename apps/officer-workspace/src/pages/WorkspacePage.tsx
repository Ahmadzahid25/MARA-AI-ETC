import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { AppLayout } from '../components/layout/AppLayout';
import { ChatPanel } from '../components/workspace/ChatPanel';
import { TaskPanel } from '../components/workspace/TaskPanel';
import { startAssessmentFull } from '../services/data';
import { sendChatMessage } from '../services/api';
import { useAssessments } from '../context/AssessmentContext';
import { UI, WORKSPACE } from '../constants';

// ─── Local intent fallback ────────────────────────────────────────────────────
// Used when the backend /api/chat is unreachable (local dev without the full
// stack). Keyword-based: deliberately simple so the backend LLM is the real
// judge in production.

const ASSESSMENT_KEYWORDS = [
  'assess', 'assessment', 'loan', 'document', 'review', 'evaluate', 'check',
  'analyse', 'analyze', 'application', 'grant', 'compliance', 'risk', 'finance',
  'market', 'report', 'submit', 'upload', 'pdf', 'semak', 'nilai', 'pinjaman',
];

// Only pure social openers — NOT question words like "how" or "apa" which can
// start legitimate questions ("how many agents do we have?").
const GREETING_KEYWORDS = [
  'hi', 'hello', 'hai', 'hey',
  'salam', 'selamat', 'assalamualaikum', 'waalaikumsalam',
];

// Questions about what the system can do / what agents exist.
const CAPABILITY_KEYWORDS = [
  'how many', 'how much', 'what agent', 'which agent', 'list agent',
  'what can you', 'what do you', 'tell me about', 'berapa agent',
  'agent ada', 'ada berapa', 'agent kita', 'agent we', 'agents we',
  'capabilities', 'features', 'fungsi', 'kemampuan',
];

function detectIntentLocally(
  text: string,
): 'greeting' | 'capability' | 'assessment' | 'unknown' {
  const lower = text.toLowerCase().trim();
  const words = lower.split(/\s+/);

  // Pure greeting — short message whose first word is a social opener.
  if (text.length < 40 && GREETING_KEYWORDS.some((kw) => words[0]?.startsWith(kw))) {
    return 'greeting';
  }
  // Capability / "what can you do" questions.
  if (CAPABILITY_KEYWORDS.some((kw) => lower.includes(kw))) {
    return 'capability';
  }
  // Workflow trigger.
  if (ASSESSMENT_KEYWORDS.some((kw) => lower.includes(kw))) {
    return 'assessment';
  }
  return 'unknown';
}

const GREETING_REPLY =
  'Selamat datang, Pegawai! I\'m MARA AI — your intelligent assistant for processing ' +
  'loan and grant applications.\n\n' +
  'Ask me anything or type what you need. For example:\n' +
  '"Assess the loan application from Ahmad bin Abdullah"\n' +
  '"Review this document" (then attach a PDF)\n' +
  '"Research the F&B sector in Selangor"';

const CAPABILITY_REPLY =
  'MARA AI-ETC runs **7 specialised AI agents**, each owning a distinct stage:\n\n' +
  '1. 🗂 **Document Agent** — OCR, extraction & classification of uploaded files\n' +
  '2. ✅ **Compliance Agent** — checks MARA policy, bumiputera status & eligibility rules\n' +
  '3. 💰 **Finance Agent** — analyses cash flow, financial ratios & repayment capacity\n' +
  '4. ⚠️ **Risk Agent** — scores credit & business risk, flags severity (low → critical)\n' +
  '5. 📈 **Market Agent** — researches sector/region context for the application\n' +
  '6. 📋 **Recommendation Agent** — synthesises all agents into a final approve/reject recommendation\n' +
  '7. 🧭 **Planner** (that\'s me) — understands your intent and routes to the right workflow\n\n' +
  'All 7 run automatically when you start a **Loan Assessment**. You stay in control at every human approval gate.';

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
    // ── Try the backend Planner first ─────────────────────────────────────
    // The backend uses a proper LLM + system prompt to decide intent, just
    // like Claude/Copilot — the model chooses when to use a tool.
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
      // ── Backend unreachable — local keyword fallback ────────────────────
      // Allows full local dev without the API gateway running. In production
      // the backend call above handles everything.
      const intent = detectIntentLocally(text);

      if (intent === 'greeting') return GREETING_REPLY;
      if (intent === 'capability') return CAPABILITY_REPLY;

      if (intent === 'unknown') {
        return (
          'I can help you assess loan applications, review documents, or research markets. ' +
          'Could you tell me more, or attach a document to begin?'
        );
      }

      // Local assessment intent path.
      setUploading(true);
      try {
        const res = await startAssessmentFull({
          file: new File([], UI.PLACEHOLDER_MOCK_FILE_NAME),
          sector: UI.DEFAULT_SECTOR,
          region: UI.DEFAULT_REGION,
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
        return `Assessment started (${res.thread_id.slice(0, 8)}…). Status: ${res.status}, ${gateLabel}.`;
      } catch {
        toast.error(WORKSPACE.TOAST_ASSESSMENT_FAILED);
        return 'Failed to start assessment. The backend may be unavailable.';
      } finally {
        setUploading(false);
      }
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
