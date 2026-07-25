import { Typography } from '@openhands/ui';
import type { SystemSetting } from '../../types/admin';

interface SystemSettingsTabProps {
  settings: SystemSetting[];
}

export function SystemSettingsTab({ settings }: SystemSettingsTabProps) {
  return (
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="border-b px-4 py-3">
        <Typography.Text fontWeight={600} fontSize="m">
          System Settings
        </Typography.Text>
      </div>
      <div className="divide-y">
        {settings.map((s) => (
          <div key={s.key} className="flex items-center justify-between px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-gray-900">{s.label}</p>
              <p className="text-xs text-gray-400">{s.description}</p>
            </div>
            <div className="ml-4 shrink-0">
              {s.type === 'toggle' ? (
                <span
                  className={`text-sm font-medium ${s.value ? 'text-green-600' : 'text-gray-400'}`}
                >
                  {s.value ? 'Enabled' : 'Disabled'}
                </span>
              ) : (
                <span className="rounded-md bg-gray-100 px-2.5 py-1 text-sm font-medium text-gray-700">
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
