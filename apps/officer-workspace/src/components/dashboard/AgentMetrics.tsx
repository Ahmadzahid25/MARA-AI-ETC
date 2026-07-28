import { Typography } from '@openhands/ui';
import type { AgentMetric } from '../../types/dashboard';
import { CONFIDENCE } from '../../constants';

interface AgentMetricsProps {
  metrics: AgentMetric[];
}

export function AgentMetrics({ metrics }: AgentMetricsProps) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417] p-5 shadow-xs">
      <div className="mb-3">
        <Typography.Text fontWeight={600} fontSize="m" className="text-slate-800 dark:text-white">
          Agent Performance
        </Typography.Text>
      </div>

      {metrics.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-200 dark:border-[#2C2E34] py-8 text-center text-xs text-slate-400 dark:text-slate-500">
          Tiada data prestasi ejen
        </div>
      )}

      {metrics.length > 0 && (
      <>
      {/* Mobile Card View (visible on screens < md) */}
      <div className="divide-y divide-slate-100 dark:divide-[#222328] md:hidden">
        {metrics.map((m) => (
          <div key={m.agent_name} className="py-3.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-800 dark:text-slate-200">{m.agent_name}</span>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                  m.avg_confidence >= CONFIDENCE.HIGH_THRESHOLD
                    ? 'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/80 dark:text-emerald-400'
                    : m.avg_confidence >= CONFIDENCE.MEDIUM_THRESHOLD
                      ? 'bg-amber-50 text-amber-600 dark:bg-amber-950/80 dark:text-amber-400'
                      : 'bg-rose-50 text-rose-600 dark:bg-rose-950/80 dark:text-rose-400'
                }`}
              >
                {(m.avg_confidence * 100).toFixed(0)}% Conf
              </span>
            </div>
            <div className="grid grid-cols-3 gap-2 rounded-lg bg-slate-50 dark:bg-[#18191C] p-2.5 text-xs">
              <div>
                <p className="text-slate-400 dark:text-slate-500 font-medium">Diproses</p>
                <p className="mt-0.5 font-semibold text-slate-700 dark:text-slate-300">{m.workflows_processed}</p>
              </div>
              <div>
                <p className="text-slate-400 dark:text-slate-500 font-medium">Latensi</p>
                <p className="mt-0.5 font-semibold text-slate-700 dark:text-slate-300">{m.avg_latency_seconds.toFixed(1)}s</p>
              </div>
              <div>
                <p className="text-slate-400 dark:text-slate-500 font-medium">Kos</p>
                <p className="mt-0.5 font-semibold text-slate-700 dark:text-slate-300">${m.total_cost.toFixed(2)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      </>
      )}

      {/* Desktop Table View (visible on screens >= md) */}
      {metrics.length > 0 && (
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-[#222328] text-xs text-slate-400 dark:text-slate-500">
              <th className="pb-2.5 font-medium">Ejen</th>
              <th className="pb-2.5 font-medium">Diproses</th>
              <th className="pb-2.5 font-medium">Latensi</th>
              <th className="pb-2.5 font-medium">Kos</th>
              <th className="pb-2.5 font-medium">Keyakinan</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50 dark:divide-[#18191C]">
            {metrics.map((m) => (
              <tr key={m.agent_name} className="transition-colors hover:bg-slate-50/50 dark:hover:bg-[#18191C]/50">
                <td className="py-3 font-medium text-slate-800 dark:text-slate-200">
                  {m.agent_name}
                </td>
                <td className="py-3 text-slate-600 dark:text-slate-400">
                  {m.workflows_processed}
                </td>
                <td className="py-3 text-slate-600 dark:text-slate-400">
                  {m.avg_latency_seconds.toFixed(1)}s
                </td>
                <td className="py-3 text-slate-600 dark:text-slate-400">
                  ${m.total_cost.toFixed(2)}
                </td>
                <td className="py-3">
                  <span
                    className={`font-semibold ${
                      m.avg_confidence >= CONFIDENCE.HIGH_THRESHOLD
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : m.avg_confidence >= CONFIDENCE.MEDIUM_THRESHOLD
                          ? 'text-amber-600 dark:text-amber-400'
                          : 'text-rose-600 dark:text-rose-400'
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
      )}
    </div>
  );
}
