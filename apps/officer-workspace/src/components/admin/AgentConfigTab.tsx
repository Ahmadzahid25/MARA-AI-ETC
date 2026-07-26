import { Typography } from '@openhands/ui';
import type { AgentProfile } from '../../types/admin';

const AUTONOMY_BADGES: Record<string, string> = {
  BOUNDED: 'bg-red-100 text-red-700 dark:bg-rose-950/80 dark:text-rose-300 dark:border dark:border-rose-800/60',
  GUIDED: 'bg-amber-100 text-amber-700 dark:bg-amber-950/80 dark:text-amber-300 dark:border dark:border-amber-800/60',
  EXPLORATORY: 'bg-purple-100 text-purple-700 dark:bg-purple-950/80 dark:text-purple-300 dark:border dark:border-purple-800/60',
};

const TIER_COLORS: Record<string, string> = {
  Haiku: 'text-gray-600 dark:text-slate-400',
  Sonnet: 'text-blue-600 dark:text-indigo-400',
  Opus: 'text-purple-600 dark:text-purple-400',
};

interface AgentConfigTabProps {
  agents: AgentProfile[];
}

export function AgentConfigTab({ agents }: AgentConfigTabProps) {
  return (
    <div className="space-y-4">
      {agents.map((agent) => (
        <div key={agent.name} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-[#222328] dark:bg-[#131417]">
          <div className="flex items-start justify-between">
            <div>
              <Typography.Text fontWeight={600} fontSize="m" className="text-slate-900 dark:text-white">
                {agent.name}
              </Typography.Text>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">
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
              <span className="text-gray-400 dark:text-slate-500">Confidence</span>
              <p className="font-medium text-gray-900 dark:text-white">
                {(agent.confidence_threshold * 100).toFixed(0)}%
              </p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-slate-500">Model</span>
              <p className={`font-medium ${TIER_COLORS[agent.model_tier] ?? 'text-gray-900 dark:text-white'}`}>
                {agent.model_tier}
              </p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-slate-500">Approval Gate</span>
              <p className={`font-medium ${agent.approval_gate_required ? 'text-amber-600 dark:text-amber-400' : 'text-green-600 dark:text-emerald-400'}`}>
                {agent.approval_gate_required ? 'Required' : 'None'}
              </p>
            </div>
            <div>
              <span className="text-gray-400 dark:text-slate-500">Network</span>
              <p className={`font-medium ${agent.network_egress ? 'text-purple-600 dark:text-purple-400' : 'text-gray-600 dark:text-slate-400'}`}>
                {agent.network_egress ? 'Egress allowed' : 'Isolated'}
              </p>
            </div>
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {agent.tools.map((tool) => (
              <span
                key={tool}
                className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-[#18191C] dark:text-slate-300 dark:border dark:border-[#2C2E34]"
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
