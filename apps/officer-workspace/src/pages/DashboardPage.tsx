import { AppLayout } from '../components/layout/AppLayout';
import { StatCard } from '../components/dashboard/StatCard';
import { WorkflowList } from '../components/dashboard/WorkflowList';
import { PendingSummary } from '../components/dashboard/PendingSummary';
import { AgentMetrics } from '../components/dashboard/AgentMetrics';
import {
  MOCK_DASHBOARD_STATS,
  MOCK_WORKFLOWS,
  MOCK_AGENT_METRICS,
  MOCK_RISK_FLAGS,
  MOCK_PENDING_APPROVALS,
} from '../mocks/mock-data';

export function DashboardPage() {
  const activeWorkflows = MOCK_WORKFLOWS.filter(
    (w) => w.status === 'in_progress' || w.status === 'awaiting_approval',
  );

  return (
    <AppLayout title="Portfolio Overview" subtitle="Pemantauan permohonan pembiayaan & geran usahawan MARA">
      <div className="space-y-6">
        {/* Stat cards grid: 2 cols on mobile -> 3 on tablet -> 5 on desktop */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <StatCard
            label="Total Workflows"
            value={MOCK_DASHBOARD_STATS.total_workflows}
          />
          <StatCard
            label="Active Workflows"
            value={MOCK_DASHBOARD_STATS.active_workflows}
            variant="warning"
          />
          <StatCard
            label="Pending Approval"
            value={MOCK_DASHBOARD_STATS.pending_approval_count}
            variant="warning"
          />
          <StatCard
            label="Blocked Workflows"
            value={MOCK_DASHBOARD_STATS.blocked_workflows}
            variant="danger"
          />
          <StatCard
            label="Risk Flags"
            value={MOCK_DASHBOARD_STATS.risk_flags_outstanding}
            variant="danger"
          />
        </div>

        {/* 2-column grid on desktop, 1-column on mobile */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <WorkflowList workflows={activeWorkflows} />
          <PendingSummary
            approvals={MOCK_PENDING_APPROVALS}
            riskFlags={MOCK_RISK_FLAGS}
          />
        </div>

        <AgentMetrics metrics={MOCK_AGENT_METRICS} />
      </div>
    </AppLayout>
  );
}
