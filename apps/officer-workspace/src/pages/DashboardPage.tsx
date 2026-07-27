import { useEffect, useState } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { StatCard } from '../components/dashboard/StatCard';
import { WorkflowList } from '../components/dashboard/WorkflowList';
import { PendingSummary } from '../components/dashboard/PendingSummary';
import { AgentMetrics } from '../components/dashboard/AgentMetrics';
import {
  fetchDashboardStats,
  fetchWorkflows,
  fetchAgentMetrics,
  fetchRiskFlags,
  fetchPendingApprovals,
} from '../services/data';
import type { DashboardStats } from '../types/dashboard';
import type { WorkflowInstance } from '../types/dashboard';
import type { AgentMetric } from '../types/dashboard';
import type { RiskFlag } from '../types/dashboard';
import type { PendingApprovalSummary } from '../types/dashboard';

export function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [workflows, setWorkflows] = useState<WorkflowInstance[]>([]);
  const [metrics, setMetrics] = useState<AgentMetric[]>([]);
  const [riskFlags, setRiskFlags] = useState<RiskFlag[]>([]);
  const [approvals, setApprovals] = useState<PendingApprovalSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [s, w, m, r, a] = await Promise.all([
          fetchDashboardStats(),
          fetchWorkflows(),
          fetchAgentMetrics(),
          fetchRiskFlags(),
          fetchPendingApprovals(),
        ]);
        setStats(s);
        setWorkflows(w);
        setMetrics(m);
        setRiskFlags(r);
        setApprovals(a);
      } catch {
        setError('Dashboard data is unavailable. The API endpoint has not been built yet.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const activeWorkflows = workflows.filter(
    (w) => w.status === 'in_progress' || w.status === 'awaiting_approval',
  );

  if (loading) {
    return (
      <AppLayout title="Portfolio Overview" subtitle="Pemantauan permohonan pembiayaan & geran usahawan MARA">
        <div className="flex items-center justify-center py-20">
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading dashboard...</p>
        </div>
      </AppLayout>
    );
  }

  if (error || !stats) {
    return (
      <AppLayout title="Portfolio Overview" subtitle="Pemantauan permohonan pembiayaan & geran usahawan MARA">
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <p className="text-sm font-medium text-amber-600 dark:text-amber-400">{error ?? 'Dashboard data is unavailable.'}</p>
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">The Dashboard API endpoint is not yet available. Data will appear once the backend is connected.</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Portfolio Overview" subtitle="Pemantauan permohonan pembiayaan & geran usahawan MARA">
      <div className="space-y-6">
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <StatCard label="Total Workflows" value={stats.total_workflows} />
          <StatCard label="Active Workflows" value={stats.active_workflows} variant="warning" />
          <StatCard label="Pending Approval" value={stats.pending_approval_count} variant="warning" />
          <StatCard label="Blocked Workflows" value={stats.blocked_workflows} variant="danger" />
          <StatCard label="Risk Flags" value={stats.risk_flags_outstanding} variant="danger" />
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <WorkflowList workflows={activeWorkflows} />
          <PendingSummary approvals={approvals} riskFlags={riskFlags} />
        </div>

        <AgentMetrics metrics={metrics} />
      </div>
    </AppLayout>
  );
}
