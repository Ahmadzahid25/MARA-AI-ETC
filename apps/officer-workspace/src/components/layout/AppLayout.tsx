import type { ReactNode } from 'react';
import { NavLink } from 'react-router';
import { Typography } from '@openhands/ui';

interface AppLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

const NAV_ITEMS = [
  { to: '/', label: 'Workspace' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/review', label: 'Review Console' },
];

export function AppLayout({ title, subtitle, children }: AppLayoutProps) {
  return (
    <div className="flex h-screen bg-gray-50">
      <aside className="flex w-56 flex-col border-r bg-white">
        <div className="border-b px-4 py-4">
          <Typography.Text fontWeight={700} fontSize="l">
            MARA AI-ETC
          </Typography.Text>
        </div>
        <nav className="flex-1 space-y-1 p-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t px-4 py-3">
          <p className="text-xs text-gray-400">Officer</p>
        </div>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b bg-white px-6 py-3 shadow-sm">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
            <p className="text-xs text-gray-500">{subtitle}</p>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
