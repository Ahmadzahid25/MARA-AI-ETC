import { Typography } from '@openhands/ui';
import type { AgentMetric } from '../../types/dashboard';

interface AgentMetricsProps {
  metrics: AgentMetric[];
}

export function AgentMetrics({ metrics }: AgentMetricsProps) {
  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="border-b px-4 py-3">
        <Typography.Text fontWeight={600} fontSize="m">
          Agent Performance
        </Typography.Text>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs uppercase text-gray-500">
              <th className="px-4 py-2 font-medium">Agent</th>
              <th className="px-4 py-2 font-medium">Workflows</th>
              <th className="px-4 py-2 font-medium">Avg Latency</th>
              <th className="px-4 py-2 font-medium">Total Cost</th>
              <th className="px-4 py-2 font-medium">Avg Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {metrics.map((m) => (
              <tr key={m.agent_name} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-medium text-gray-900">
                  {m.agent_name}
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  {m.workflows_processed}
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  {m.avg_latency_seconds.toFixed(1)}s
                </td>
                <td className="px-4 py-2.5 text-gray-600">
                  ${m.total_cost.toFixed(2)}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`font-medium ${
                      m.avg_confidence >= 0.85
                        ? 'text-green-600'
                        : m.avg_confidence >= 0.6
                          ? 'text-amber-600'
                          : 'text-red-600'
                    }`}
                  >
                    {(m.avg_confidence * 100).toFixed(0)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
