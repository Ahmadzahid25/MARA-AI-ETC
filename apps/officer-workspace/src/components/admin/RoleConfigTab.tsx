import { Typography } from '@openhands/ui';
import type { AdminRole } from '../../types/admin';

interface RoleConfigTabProps {
  roles: AdminRole[];
}

export function RoleConfigTab({ roles }: RoleConfigTabProps) {
  return (
    <div className="space-y-4">
      {roles.map((role) => (
        <div key={role.id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-[#222328] dark:bg-[#131417]">
          <div className="flex items-start justify-between">
            <div>
              <Typography.Text fontWeight={600} fontSize="m" className="text-slate-900 dark:text-white">
                {role.name}
              </Typography.Text>
              <p className="mt-0.5 text-xs text-gray-500 dark:text-slate-400">
                {role.description}
              </p>
            </div>
            <span className="shrink-0 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700 dark:bg-indigo-950/80 dark:text-indigo-300 dark:border dark:border-indigo-800/60">
              {role.member_count} members
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {role.grants.map((grant) => (
              <span
                key={grant}
                className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600 dark:bg-[#18191C] dark:text-slate-300 dark:border dark:border-[#2C2E34]"
              >
                {grant}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
