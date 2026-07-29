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
      const validPdfBytes = new Uint8Array([
        0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34, 0x0a, 0x25, 0xe2, 0xe3, 0xcf, 0xd3, 0x0a,
        0x31, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a, 0x3c, 0x3c, 0x2f, 0x54, 0x79, 0x70, 0x65,
        0x2f, 0x43, 0x61, 0x74, 0x61, 0x6c, 0x6f, 0x67, 0x2f, 0x50, 0x61, 0x67, 0x65, 0x73, 0x20,
        0x32, 0x20, 0x30, 0x20, 0x52, 0x3e, 0x3e, 0x0a, 0x65, 0x6e, 0x64, 0x6f, 0x62, 0x6a, 0x0a,
        0x32, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a, 0x3c, 0x3c, 0x2f, 0x54, 0x79, 0x70, 0x65,
        0x2f, 0x50, 0x61, 0x67, 0x65, 0x73, 0x2f, 0x43, 0x6f, 0x75, 0x6e, 0x74, 0x20, 0x31, 0x2f,
        0x4b, 0x69, 0x64, 0x73, 0x5b, 0x33, 0x20, 0x30, 0x20, 0x52, 0x5d, 0x3e, 0x3e, 0x0a, 0x65,
        0x6e, 0x64, 0x6f, 0x62, 0x6a, 0x0a, 0x33, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a, 0x3c,
        0x3c, 0x2f, 0x54, 0x79, 0x70, 0x65, 0x2f, 0x50, 0x61, 0x67, 0x65, 0x2f, 0x50, 0x61, 0x72,
        0x65, 0x6e, 0x74, 0x20, 0x32, 0x20, 0x30, 0x20, 0x52, 0x2f, 0x4d, 0x65, 0x64, 0x69, 0x61,
        0x42, 0x6f, 0x78, 0x5b, 0x30, 0x20, 0x30, 0x20, 0x36, 0x31, 0x32, 0x20, 0x37, 0x39, 0x32,
        0x5d, 0x2f, 0x52, 0x65, 0x73, 0x6f, 0x75, 0x72, 0x63, 0x65, 0x73, 0x3c, 0x3c, 0x2f, 0x46,
        0x6f, 0x6e, 0x74, 0x3c, 0x3c, 0x2f, 0x46, 0x31, 0x20, 0x34, 0x20, 0x30, 0x20, 0x52, 0x3e,
        0x3e, 0x3e, 0x3e, 0x2f, 0x43, 0x6f, 0x6e, 0x74, 0x65, 0x6e, 0x74, 0x73, 0x20, 0x35, 0x20,
        0x30, 0x20, 0x52, 0x3e, 0x3e, 0x0a, 0x65, 0x6e, 0x64, 0x6f, 0x62, 0x6a, 0x0a, 0x34, 0x20,
        0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a, 0x3c, 0x3c, 0x2f, 0x54, 0x79, 0x70, 0x65, 0x2f, 0x46,
        0x6f, 0x6e, 0x74, 0x2f, 0x53, 0x75, 0x62, 0x74, 0x79, 0x70, 0x65, 0x2f, 0x54, 0x79, 0x70,
        0x65, 0x31, 0x2f, 0x42, 0x61, 0x73, 0x65, 0x46, 0x6f, 0x6e, 0x74, 0x2f, 0x48, 0x65, 0x6c,
        0x76, 0x65, 0x74, 0x69, 0x63, 0x61, 0x3e, 0x3e, 0x0a, 0x65, 0x6e, 0x64, 0x6f, 0x62, 0x6a,
        0x0a, 0x35, 0x20, 0x30, 0x20, 0x6f, 0x62, 0x6a, 0x0a, 0x3c, 0x3c, 0x2f, 0x4c, 0x65, 0x6e,
        0x67, 0x74, 0x68, 0x20, 0x34, 0x34, 0x3e, 0x3e, 0x0a, 0x73, 0x74, 0x72, 0x65, 0x61, 0x6d,
        0x0a, 0x42, 0x54, 0x20, 0x2f, 0x46, 0x31, 0x20, 0x31, 0x32, 0x20, 0x54, 0x66, 0x20, 0x37,
        0x30, 0x20, 0x37, 0x30, 0x30, 0x20, 0x54, 0x64, 0x20, 0x28, 0x50, 0x65, 0x72, 0x6d, 0x6f,
        0x68, 0x6f, 0x6e, 0x61, 0x6e, 0x20, 0x50, 0x65, 0x6d, 0x62, 0x69, 0x61, 0x79, 0x61, 0x61,
        0x6e, 0x29, 0x20, 0x54, 0x6a, 0x20, 0x45, 0x54, 0x0a, 0x65, 0x6e, 0x64, 0x73, 0x74, 0x72,
        0x65, 0x61, 0x6d, 0x0a, 0x65, 0x6e, 0x64, 0x6f, 0x62, 0x6a, 0x0a, 0x78, 0x72, 0x65, 0x66,
        0x0a, 0x30, 0x20, 0x36, 0x0a, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30,
        0x20, 0x36, 0x35, 0x35, 0x33, 0x35, 0x20, 0x66, 0x20, 0x0a, 0x30, 0x30, 0x30, 0x30, 0x30,
        0x30, 0x30, 0x30, 0x31, 0x36, 0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x6e, 0x20, 0x0a,
        0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x36, 0x35, 0x20, 0x30, 0x30, 0x30, 0x30,
        0x30, 0x20, 0x6e, 0x20, 0x0a, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x31, 0x32, 0x32,
        0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x6e, 0x20, 0x0a, 0x30, 0x30, 0x30, 0x30, 0x30,
        0x30, 0x30, 0x32, 0x33, 0x37, 0x20, 0x30, 0x30, 0x30, 0x30, 0x30, 0x20, 0x6e, 0x20, 0x0a,
        0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x33, 0x30, 0x39, 0x20, 0x30, 0x30, 0x30, 0x30,
        0x30, 0x20, 0x6e, 0x20, 0x0a, 0x74, 0x72, 0x61, 0x69, 0x6c, 0x65, 0x72, 0x0a, 0x3c, 0x3c,
        0x2f, 0x53, 0x69, 0x7a, 0x65, 0x20, 0x36, 0x2f, 0x52, 0x6f, 0x6f, 0x74, 0x20, 0x31, 0x20,
        0x30, 0x20, 0x52, 0x3e, 0x3e, 0x0a, 0x73, 0x74, 0x61, 0x72, 0x74, 0x78, 0x72, 0x65, 0x66,
        0x0a, 0x34, 0x30, 0x33, 0x0a, 0x25, 0x25, 0x45, 0x4f, 0x46, 0x0a
      ]);
      const mockFile = new File([validPdfBytes], UI.PLACEHOLDER_MOCK_FILE_NAME, { type: 'application/pdf' });
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
