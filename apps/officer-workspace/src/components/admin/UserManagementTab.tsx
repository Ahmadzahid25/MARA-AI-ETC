import { Typography } from '@openhands/ui';
import type { AdminUser } from '../../types/admin';

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
    <div className="rounded-lg border bg-white shadow-sm">
      <div className="border-b px-4 py-3">
        <Typography.Text fontWeight={600} fontSize="m">
          Users ({users.length})
        </Typography.Text>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b bg-gray-50 text-xs uppercase text-gray-500">
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Role</th>
              <th className="px-4 py-2 font-medium">Branch</th>
              <th className="px-4 py-2 font-medium">MFA</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Last Login</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50">
                <td className="px-4 py-2.5 font-medium text-gray-900">
                  {u.name}
                </td>
                <td className="px-4 py-2.5 text-gray-600">{u.email}</td>
                <td className="px-4 py-2.5 text-gray-600">{u.role}</td>
                <td className="px-4 py-2.5 text-gray-600">{u.branch}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={`text-xs font-medium ${u.mfa_enrolled ? 'text-green-600' : 'text-amber-600'}`}
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
                <td className="px-4 py-2.5 text-gray-500">
                  {u.last_login
                    ? new Date(u.last_login).toLocaleDateString('en-MY')
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
