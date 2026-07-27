import { Chip, Divider, Typography } from '@openhands/ui';
import { confidenceColor, confidenceLabel } from '../../types/documents';
import { PolicyCitationRenderer } from './PolicyCitationRenderer';
import { RetrievalSummary } from './RetrievalSummary';
import type { PendingGate } from '../../services/api';
import type {
  ExtractionPayload,
  CompliancePayload,
  FinancialPayload,
  RiskPayload,
  RecommendationPayload,
  PublishPayload,
} from '../../types/gates';

interface GateRendererProps {
  gate: PendingGate;
  payload: Record<string, unknown> | null;
}

export function GateRenderer({ gate, payload }: GateRendererProps) {
  switch (gate) {
    case 'confirm_extraction':
      return <ExtractionGate payload={payload as ExtractionPayload | null} />;
    case 'compliance_acknowledgment':
      return <ComplianceGate payload={payload as CompliancePayload | null} />;
    case 'financial_sign_off':
      return <FinancialGate payload={payload as FinancialPayload | null} />;
    case 'risk_review':
      return <RiskGate payload={payload as RiskPayload | null} />;
    case 'recommendation_approval':
      return <RecommendationGate payload={payload as RecommendationPayload | null} />;
    case 'publish_approval':
      return <PublishGate payload={payload as PublishPayload | null} />;
    default:
      return (
        <div className="rounded-md bg-slate-50 p-4 dark:bg-[#18191C]">
          <Typography.Text fontSize="s" className="text-slate-500 dark:text-slate-400">
            Unknown gate: {gate}. No renderer available.
          </Typography.Text>
        </div>
      );
  }
}

function ExtractionGate({ payload }: { payload: ExtractionPayload | null }) {
  if (!payload) return <EmptyPayload />;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Chip color="gray" variant="pill">{payload.document_id}</Chip>
        <Chip color="green" variant="pill">
          {payload.classification.document_type} ({(payload.classification.confidence * 100).toFixed(0)}%)
        </Chip>
      </div>
      {payload.fields.map((field) => (
        <div key={field.name} className="rounded-md border border-gray-200 bg-white p-3 dark:border-[#222328] dark:bg-[#18191C]">
          <div className="flex items-center gap-2">
            <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
              {field.name}
            </Typography.Text>
            <Chip color={confidenceColor(field.confidence) as 'green' | 'primaryDark' | 'red'} variant="pill">
              {confidenceLabel(field.confidence)} ({(field.confidence * 100).toFixed(0)}%)
            </Chip>
            <Chip color="gray" variant="pill">
              {field.source === 'ocr' ? 'OCR' : 'PDF Text'}
            </Chip>
          </div>
          <Typography.Text fontSize="m" className="mt-1 text-slate-800 dark:text-slate-200">
            {field.value}
          </Typography.Text>
          <Typography.Text fontSize="xxs" className="mt-1 text-gray-400 dark:text-slate-500">
            Source: {field.citation.document_id} p.{field.citation.page}
          </Typography.Text>
        </div>
      ))}
    </div>
  );
}

function ComplianceGate({ payload }: { payload: CompliancePayload | null }) {
  if (!payload) return <EmptyPayload />;

  return (
    <div className="space-y-3">
      <RetrievalSummary result={payload.retrieval_result ?? null} />
      {payload.items.map((item, i) => {
        const statusColor: Record<string, 'green' | 'red' | 'primaryDark' | 'gray'> = {
          pass: 'green',
          fail: 'red',
          exception: 'primaryDark',
          no_policy_found: 'gray',
        };
        return (
          <div key={i} className="rounded-md border border-gray-200 bg-white p-3 dark:border-[#222328] dark:bg-[#18191C]">
            <div className="flex items-center justify-between">
              <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
                {item.requirement}
              </Typography.Text>
              <Chip color={statusColor[item.status] ?? 'gray'} variant="pill">
                {item.status.replace(/_/g, ' ')}
              </Chip>
            </div>
            {item.notes && (
              <Typography.Text fontSize="xs" className="mt-1 text-slate-500 dark:text-slate-400">
                {item.notes}
              </Typography.Text>
            )}
            <PolicyCitationRenderer citation={item.policy_citation ?? null} />
          </div>
        );
      })}
    </div>
  );
}

function FinancialGate({ payload }: { payload: FinancialPayload | null }) {
  if (!payload) return <EmptyPayload />;

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-gray-200 bg-white p-3 dark:border-[#222328] dark:bg-[#18191C]">
        <Typography.Text fontSize="s" className="text-slate-800 dark:text-slate-200">
          {payload.summary}
        </Typography.Text>
        {payload.metrics && (
          <div className="mt-3 space-y-1">
            {Object.entries(payload.metrics).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-slate-500 dark:text-slate-400">{key}</span>
                <span className="font-medium text-slate-900 dark:text-slate-100">{value}</span>
              </div>
            ))}
          </div>
        )}
        <div className="mt-2">
          <Chip color={confidenceColor(payload.confidence) as 'green' | 'primaryDark' | 'red'} variant="pill">
            Confidence: {(payload.confidence * 100).toFixed(0)}%
          </Chip>
        </div>
      </div>
    </div>
  );
}

function RiskGate({ payload }: { payload: RiskPayload | null }) {
  if (!payload) return <EmptyPayload />;

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-gray-200 bg-white p-3 dark:border-[#222328] dark:bg-[#18191C]">
        <div className="flex items-center gap-2">
          <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
            Risk Rating
          </Typography.Text>
          <Chip color={payload.score > 0.7 ? 'red' : payload.score > 0.4 ? 'primaryDark' : 'green'} variant="pill">
            {payload.rating} ({(payload.score * 100).toFixed(0)}%)
          </Chip>
        </div>
      </div>
      {payload.flags?.map((flag, i) => {
        const severityColor: Record<string, 'red' | 'primaryDark' | 'green' | 'gray'> = {
          critical: 'red',
          high: 'red',
          medium: 'primaryDark',
          low: 'green',
        };
        return (
          <div key={i} className="rounded-md border border-red-200 bg-red-50 p-3 dark:border-red-800/60 dark:bg-red-950/40">
            <div className="flex items-center justify-between">
              <Typography.Text fontSize="s" className="text-slate-800 dark:text-slate-200">
                {flag.description}
              </Typography.Text>
              <Chip color={severityColor[flag.severity] ?? 'gray'} variant="pill">
                {flag.severity}
              </Chip>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RecommendationGate({ payload }: { payload: RecommendationPayload | null }) {
  if (!payload) return <EmptyPayload />;

  const isApproved = payload.decision === 'approve';

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-gray-200 bg-white p-3 dark:border-[#222328] dark:bg-[#18191C]">
        <div className="flex items-center gap-2">
          <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
            Recommendation
          </Typography.Text>
          <Chip color={isApproved ? 'green' : 'red'} variant="pill">
            {payload.decision}
          </Chip>
        </div>
        <Divider />
        <Typography.Text fontSize="s" className="mt-2 text-slate-800 dark:text-slate-200">
          {payload.rationale}
        </Typography.Text>
        <div className="mt-2">
          <Chip color={confidenceColor(payload.confidence) as 'green' | 'primaryDark' | 'red'} variant="pill">
            Confidence: {(payload.confidence * 100).toFixed(0)}%
          </Chip>
        </div>
      </div>
    </div>
  );
}

function PublishGate({ payload }: { payload: PublishPayload | null }) {
  if (!payload) return <EmptyPayload />;

  return (
    <div className="space-y-3">
      <div className="rounded-md border border-gray-200 bg-white p-3 dark:border-[#222328] dark:bg-[#18191C]">
        <Typography.Text fontSize="s" fontWeight={600} className="text-slate-900 dark:text-slate-100">
          Generated Documents
        </Typography.Text>
        <div className="mt-2 space-y-2">
          {payload.documents.map((doc, i) => (
            <div key={i} className="flex items-center gap-2 rounded-md bg-slate-50 p-2 dark:bg-[#222328]">
              <Typography.Text fontSize="s" className="text-slate-700 dark:text-slate-300">
                {doc}
              </Typography.Text>
            </div>
          ))}
        </div>
        <div className="mt-2">
          <Chip color="gray" variant="pill">Status: {payload.status}</Chip>
        </div>
      </div>
    </div>
  );
}

function EmptyPayload() {
  return (
    <Typography.Text fontSize="s" className="text-slate-400 dark:text-slate-500">
      No payload data available for this gate.
    </Typography.Text>
  );
}
