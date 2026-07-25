import { Typography } from '@openhands/ui';
import type { AdminRole } from '../../types/admin';

interface RoleConfigTabProps {
  roles: AdminRole[];
}

export function RoleConfigTab({ roles }: RoleConfigTabProps) {
  return (
    <div className="space-y-4">
      {roles.map((role) => (
        <div key={role.id} className="rounded-lg border bg-white p-4 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <Typography.Text fontWeight={600} fontSize="m">
                {role.name}
              </Typography.Text>
              <p className="mt-0.5 text-xs text-gray-500">
                {role.description}
              </p>
            </div>
            <span className="shrink-0 rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
              {role.member_count} members
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {role.grants.map((grant) => (
              <span
                key={grant}
                className="rounded-md bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
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
