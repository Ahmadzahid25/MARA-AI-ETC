import { Typography } from '@openhands/ui';
import type { AdminUser } from '../../types/admin';
import { UI } from '../../constants';

const STATUS_BADGES: Record<string, string> = {
  active: 'bg-green-100 text-green-700',
  inactive: 'bg-gray-100 text-gray-500',
  invited: 'bg-blue-100 text-blue-700',
};

interface UserManagementTabProps {
  users: AdminUser[];
}

export function UserManagementTab({ users }: UserManagementTabProps) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white shadow-sm dark:border-[#222328] dark:bg-[#131417]">
      <div className="border-b border-gray-200 dark:border-[#222328] px-4 py-3">
        <Typography.Text fontWeight={600} fontSize="m" className="text-slate-900 dark:text-white">
          Users ({users.length})
        </Typography.Text>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-[#222328] bg-gray-50 dark:bg-[#18191C] text-xs uppercase text-gray-500 dark:text-slate-400">
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Role</th>
              <th className="px-4 py-2 font-medium">Branch</th>
              <th className="px-4 py-2 font-medium">MFA</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Last Login</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-[#222328]">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-[#18191C]/50 transition-colors">
                <td className="px-4 py-2.5 font-medium text-gray-900 dark:text-white">
                  {u.name}
                </td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-slate-400">{u.email}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-slate-400">{u.role}</td>
                <td className="px-4 py-2.5 text-gray-600 dark:text-slate-400">{u.branch}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={`text-xs font-medium ${u.mfa_enrolled ? 'text-green-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'}`}
                  >
                    {u.mfa_enrolled ? 'Enrolled' : 'Not enrolled'}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_BADGES[u.status] ?? ''}`}
                  >
                    {u.status}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-gray-500 dark:text-slate-500">
                  {u.last_login
                    ? new Date(u.last_login).toLocaleDateString(UI.LOCALE)
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
