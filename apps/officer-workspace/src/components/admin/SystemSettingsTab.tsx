import { Typography } from '@openhands/ui';
import type { SystemSetting } from '../../types/admin';

interface SystemSettingsTabProps {
  settings: SystemSetting[];
}

export function SystemSettingsTab({ settings }: SystemSettingsTabProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm dark:border-[#222328] dark:bg-[#131417]">
      <div className="border-b border-gray-200 dark:border-[#222328] px-4 py-3">
        <Typography.Text fontWeight={600} fontSize="m" className="text-slate-900 dark:text-white">
          System Settings
        </Typography.Text>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-[#222328]">
        {settings.map((s) => (
          <div key={s.key} className="flex items-center justify-between px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900 dark:text-white">{s.label}</p>
              <p className="text-xs text-gray-400 dark:text-slate-400">{s.description}</p>
            </div>
            <div className="ml-4 shrink-0">
              {s.type === 'toggle' ? (
                <span
                  className={`text-sm font-medium ${s.value ? 'text-green-600 dark:text-emerald-400' : 'text-gray-400 dark:text-slate-500'}`}
                >
                  {s.value ? 'Enabled' : 'Disabled'}
                </span>
              ) : (
                <span className="rounded-md bg-gray-100 px-2.5 py-1 text-sm font-medium text-gray-700 dark:bg-[#18191C] dark:text-slate-200 dark:border dark:border-[#2C2E34]">
                  {String(s.value)}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
