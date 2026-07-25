import { Typography } from '@openhands/ui';
import type { AgentProfile } from '../../types/admin';

const AUTONOMY_BADGES: Record<string, string> = {
  BOUNDED: 'bg-red-100 text-red-700',
  GUIDED: 'bg-amber-100 text-amber-700',
  EXPLORATORY: 'bg-purple-100 text-purple-700',
};

const TIER_COLORS: Record<string, string> = {
  Haiku: 'text-gray-600',
  Sonnet: 'text-blue-600',
  Opus: 'text-purple-600',
};

interface AgentConfigTabProps {
  agents: AgentProfile[];
}

export function AgentConfigTab({ agents }: AgentConfigTabProps) {
  return (
    <div className="space-y-4">
      {agents.map((agent) => (
        <div key={agent.name} className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <Typography.Text fontWeight={600} fontSize="m">
                {agent.name}
              </Typography.Text>
              <p className="mt-0.5 text-xs text-gray-500">
                {agent.description}
              </p>
            </div>
            <span
              className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${AUTONOMY_BADGES[agent.autonomy] ?? ''}`}
            >
              {agent.autonomy}
            </span>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-4 text-xs">
            <div>
              <span className="text-gray-400">Confidence</span>
              <p className="font-medium text-gray-900">
                {(agent.confidence_threshold * 100).toFixed(0)}%
              </p>
            </div>
            <div>
              <span className="text-gray-400">Model</span>
              <p className={`font-medium ${TIER_COLORS[agent.model_tier] ?? 'text-gray-900'}`}>
                {agent.model_tier}
              </p>
            </div>
            <div>
              <span className="text-gray-400">Approval Gate</span>
              <p className={`font-medium ${agent.approval_gate_required ? 'text-amber-600' : 'text-green-600'}`}>
                {agent.approval_gate_required ? 'Required' : 'None'}
              </p>
            </div>
            <div>
              <span className="text-gray-400">Network</span>
              <p className={`font-medium ${agent.network_egress ? 'text-purple-600' : 'text-gray-600'}`}>
                {agent.network_egress ? 'Egress allowed' : 'Isolated'}
              </p>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {agent.tools.map((tool) => (
              <span
                key={tool}
                className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
