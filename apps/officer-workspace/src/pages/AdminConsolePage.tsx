import { useEffect, useState } from 'react';
import { Tabs } from '@openhands/ui';
import { AppLayout } from '../components/layout/AppLayout';
import { UserManagementTab } from '../components/admin/UserManagementTab';
import { RoleConfigTab } from '../components/admin/RoleConfigTab';
import { AgentConfigTab } from '../components/admin/AgentConfigTab';
import { SystemSettingsTab } from '../components/admin/SystemSettingsTab';
import {
  fetchUsers,
  fetchRoles,
  fetchAgentProfiles,
  fetchSystemSettings,
} from '../services/data';
import type { AdminUser } from '../types/admin';
import type { AdminRole } from '../types/admin';
import type { AgentProfile } from '../types/admin';
import type { SystemSetting } from '../types/admin';

export function AdminConsolePage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [roles, setRoles] = useState<AdminRole[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [settings, setSettings] = useState<SystemSetting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [u, r, a, s] = await Promise.all([
          fetchUsers(),
          fetchRoles(),
          fetchAgentProfiles(),
          fetchSystemSettings(),
        ]);
        setUsers(u);
        setRoles(r);
        setAgents(a);
        setSettings(s);
      } catch {
        setError('Admin Console data is unavailable. The API endpoint has not been built yet.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <AppLayout title="Admin Console" subtitle="User / role / agent configuration">
        <div className="flex items-center justify-center py-20">
          <p className="text-sm text-slate-500 dark:text-slate-400">Loading...</p>
        </div>
      </AppLayout>
    );
  }

  if (error) {
    return (
      <AppLayout title="Admin Console" subtitle="User / role / agent configuration">
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <p className="text-sm font-medium text-amber-600 dark:text-amber-400">{error}</p>
            <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">Data will appear once the backend is connected.</p>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title="Admin Console"
      subtitle="User / role / agent configuration"
    >
      <Tabs>
        <Tabs.Item text={`Users (${users.length})`} testId="tab-users">
          <div className="mt-4">
            <UserManagementTab users={users} />
          </div>
        </Tabs.Item>

        <Tabs.Item text="Roles" testId="tab-roles">
          <div className="mt-4">
            <RoleConfigTab roles={roles} />
          </div>
        </Tabs.Item>

        <Tabs.Item text="Agents" testId="tab-agents">
          <div className="mt-4">
            <AgentConfigTab agents={agents} />
          </div>
        </Tabs.Item>

        <Tabs.Item text="System Settings" testId="tab-settings">
          <div className="mt-4">
            <SystemSettingsTab settings={settings} />
          </div>
        </Tabs.Item>
      </Tabs>
    </AppLayout>
  );
}
