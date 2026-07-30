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
    // ── Send to backend Planner AI ─────────────────────────────────────────
    // The backend LLM (GPT-4o / Claude) decides intent — the model replies
    // conversationally unless the officer explicitly uploads a document and
    // triggers a workflow via the file-attach button.
    try {
      const chatRes = await sendChatMessage(text);
      return chatRes.reply;
    } catch {
      // ── Backend unreachable — local keyword fallback ────────────────────
      const intent = detectIntentLocally(text);
      if (intent === 'greeting') return GREETING_REPLY;
      if (intent === 'capability') return CAPABILITY_REPLY;
      return (
        'I can help you assess loan applications, review documents, or research markets. ' +
        'Attach a document using the + button to begin an assessment.'
      );
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
