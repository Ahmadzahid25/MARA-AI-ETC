import { useState, useMemo } from 'react';
import { Chip, Input, Scrollable, Typography } from '@openhands/ui';
import { AppLayout } from '../components/layout/AppLayout';
import { useAssessments } from '../context/AssessmentContext';
import type { LiveAssessment } from '../types/workspace';

interface Finding {
  id: string;
  type: 'stalled_gate' | 'failed_stage' | 'missing_stage_log' | 'long_running' | 'incomplete_data';
  severity: 'low' | 'medium' | 'high' | 'critical';
  assessment: LiveAssessment;
  message: string;
  detail: string;
}

function deriveFindings(assessments: LiveAssessment[]): Finding[] {
  const findings: Finding[] = [];
  const now = Date.now();

  for (const a of assessments) {
    const log = a.stage_log ?? [];

    if (log.length === 0) {
      findings.push({
        id: `${a.thread_id}-no-log`,
        type: 'missing_stage_log',
        severity: 'high',
        assessment: a,
        message: 'No stage log recorded',
        detail: 'Assessment has no stage log entries. The workflow may not have started correctly.',
      });
      continue;
    }

    const failedStage = log.find((s) => s.status === 'failed');
    if (failedStage) {
      findings.push({
        id: `${a.thread_id}-failed-${failedStage.stage}`,
        type: 'failed_stage',
        severity: 'critical',
        assessment: a,
        message: `Stage "${failedStage.stage}" failed`,
        detail: `Agent: ${failedStage.agent}. Started: ${failedStage.started_at}. No completion recorded.`,
      });
    }

    if (a.status === 'pending_approval' && a.pending_gate) {
      const created = new Date(a.created_at).getTime();
      const stalledHours = (now - created) / (1000 * 60 * 60);
      if (stalledHours > 24) {
        findings.push({
          id: `${a.thread_id}-stalled`,
          type: 'stalled_gate',
          severity: 'medium',
          assessment: a,
          message: `Stalled at "${a.pending_gate.replace(/_/g, ' ')}" for ${Math.floor(stalledHours)}h`,
          detail: `No decision submitted. Assessment has been awaiting approval for over 24 hours.`,
        });
      }
    }

    const runningStage = log.find((s) => s.status === 'in_progress');
    if (runningStage) {
      const started = new Date(runningStage.started_at).getTime();
      const runningHours = (now - started) / (1000 * 60 * 60);
      if (runningHours > 4) {
        findings.push({
          id: `${a.thread_id}-longrun-${runningStage.stage}`,
          type: 'long_running',
          severity: 'high',
          assessment: a,
          message: `Stage "${runningStage.stage}" running for ${Math.floor(runningHours)}h`,
          detail: `Agent: ${runningStage.agent}. Started at ${runningStage.started_at} with no completion.`,
        });
      }
    }
  }

  return findings.sort((a, b) => {
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    return order[a.severity] - order[b.severity];
  });
}

const SEVERITY_CONFIG: Record<string, { color: 'red' | 'primaryDark' | 'green'; label: string }> = {
  critical: { color: 'red', label: 'Critical' },
  high: { color: 'red', label: 'High' },
  medium: { color: 'primaryDark', label: 'Medium' },
  low: { color: 'green', label: 'Low' },
};

function FindingCard({ finding }: { finding: Finding }) {
  const config = SEVERITY_CONFIG[finding.severity]!;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-[#222328] dark:bg-[#131417]">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <Chip color={config.color} variant="pill">{config.label}</Chip>
            <Typography.Text fontSize="xs" className="font-mono text-slate-400 dark:text-slate-500">
              {finding.assessment.thread_id.slice(0, 12)}…
            </Typography.Text>
          </div>
          <Typography.Text fontSize="s" fontWeight={600} className="mt-2 block text-slate-900 dark:text-white">
            {finding.message}
          </Typography.Text>
          <Typography.Text fontSize="xs" className="mt-1 block text-slate-500 dark:text-slate-400">
            {finding.detail}
          </Typography.Text>
        </div>
      </div>
    </div>
  );
}

export function AuditorConsolePage() {
  const { assessments } = useAssessments();
  const [search, setSearch] = useState('');
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);

  const findings = useMemo(() => deriveFindings(assessments), [assessments]);

  const filteredFindings = useMemo(() => {
    let result = findings;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (f) =>
          f.message.toLowerCase().includes(q) ||
          f.detail.toLowerCase().includes(q) ||
          f.assessment.thread_id.toLowerCase().includes(q),
      );
    }
    if (severityFilter) {
      result = result.filter((f) => f.severity === severityFilter);
    }
    return result;
  }, [findings, search, severityFilter]);

  const criticalCount = findings.filter((f) => f.severity === 'critical').length;
  const highCount = findings.filter((f) => f.severity === 'high').length;
  const totalCount = findings.length;

  return (
    <AppLayout title="Auditor Console" subtitle="Cross-workflow review — gaps are findings, never smoothed over">
      <div className="mb-6">
        <div className="mb-4 flex items-center gap-3">
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-800/60 dark:bg-red-950/30">
            <Typography.Text fontSize="s" fontWeight={600} className="text-red-700 dark:text-red-300">
              {criticalCount} critical
            </Typography.Text>
          </div>
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-800/60 dark:bg-amber-950/30">
            <Typography.Text fontSize="s" fontWeight={600} className="text-amber-700 dark:text-amber-300">
              {highCount} high
            </Typography.Text>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 dark:border-[#222328] dark:bg-[#18191C]">
            <Typography.Text fontSize="s" fontWeight={600} className="text-slate-600 dark:text-slate-400">
              {totalCount} total findings
            </Typography.Text>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex-1">
            <Input
              label="Search findings"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by message, detail, or thread ID…"
            />
          </div>
          <div className="flex gap-1.5">
            {[null, 'critical', 'high', 'medium', 'low'].map((s) => {
              const label = s ?? 'All';
              const isActive = severityFilter === s;
              return (
                <button
                  key={label}
                  type="button"
                  onClick={() => setSeverityFilter(s)}
                  className={`cursor-pointer rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-[#222328] dark:text-slate-400 dark:hover:bg-[#2C2E34]'
                  }`}
                >
                  {label === 'All' ? 'All' : label.charAt(0).toUpperCase() + label.slice(1)}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {assessments.length === 0 ? (
        <div className="py-20 text-center">
          <Typography.Text fontSize="m" className="text-gray-400">
            No assessments to audit. Start one from the Workspace.
          </Typography.Text>
        </div>
      ) : filteredFindings.length === 0 ? (
        <div className="py-20 text-center">
          <Typography.Text fontSize="m" className="text-gray-400">
            No findings match your filters.
          </Typography.Text>
        </div>
      ) : (
        <Scrollable className="max-h-[calc(100vh-280px)]">
          <div className="space-y-3">
            {filteredFindings.map((finding) => (
              <FindingCard key={finding.id} finding={finding} />
            ))}
          </div>
        </Scrollable>
      )}
    </AppLayout>
  );
}
