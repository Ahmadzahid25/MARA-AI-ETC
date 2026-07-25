import { useState } from 'react';
import { Tabs } from '@openhands/ui';
import { AppLayout } from '../components/layout/AppLayout';
import { UserManagementTab } from '../components/admin/UserManagementTab';
import { RoleConfigTab } from '../components/admin/RoleConfigTab';
import { AgentConfigTab } from '../components/admin/AgentConfigTab';
import { SystemSettingsTab } from '../components/admin/SystemSettingsTab';
import {
  MOCK_USERS,
  MOCK_ROLES,
  MOCK_AGENT_PROFILES,
  MOCK_SYSTEM_SETTINGS,
} from '../mocks/mock-data';

export function AdminConsolePage() {
  const [users] = useState(MOCK_USERS);

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
            <RoleConfigTab roles={MOCK_ROLES} />
          </div>
        </Tabs.Item>

        <Tabs.Item text="Agents" testId="tab-agents">
          <div className="mt-4">
            <AgentConfigTab agents={MOCK_AGENT_PROFILES} />
          </div>
        </Tabs.Item>

        <Tabs.Item text="System Settings" testId="tab-settings">
          <div className="mt-4">
            <SystemSettingsTab settings={MOCK_SYSTEM_SETTINGS} />
          </div>
        </Tabs.Item>
      </Tabs>
    </AppLayout>
  );
}
