import { useEffect, useState, type ReactNode } from 'react';
import { NavLink } from 'react-router';
import { Icon, Input } from '@openhands/ui';
import { getUserProfile, logout } from '../../services/auth';
import { useTheme } from '../../context/ThemeContext';
import type { UserProfile } from '../../services/auth';
import logo from '../../assets/mara-ai-etc.png';
import { MOCK_AUTH } from '../../constants';

interface AppLayoutProps {
  title: string;
  subtitle: string;
  children: ReactNode;
}

const NAV_ITEMS = [
  {
    to: '/',
    label: 'Workspace',
    icon: (
      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
    ),
  },
  {
    to: '/dashboard',
    label: 'Dashboard',
    icon: (
      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
      </svg>
    ),
  },
  {
    to: '/review',
    label: 'Review Console',
    icon: (
      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
      </svg>
    ),
  },
  {
    to: '/admin',
    label: 'Admin Console',
    icon: (
      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    to: '/auditor',
    label: 'Auditor Console',
    icon: (
      <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
      </svg>
    ),
  },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {

  const { theme, toggleTheme } = useTheme();
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    getUserProfile().then(setProfile);
  }, []);

  const displayName = profile?.name ?? MOCK_AUTH.DEV_NAME;
  const displayRole = `Cawangan Ibu Pejabat · ${profile?.roles[0] ?? MOCK_AUTH.DEV_ROLE}`;

  return (
    <div className="flex h-full flex-col justify-between">
      <div>
        <div className="border-b border-slate-200 dark:border-[#222328] px-5 py-4">
          <div className="flex items-center gap-3">
            <img src={logo} alt="MARA AI-ETC Logo" className="h-9 w-auto shrink-0 object-contain" />
            <div>
              <p className="text-sm font-bold tracking-tight text-slate-900 dark:text-white leading-tight">MARA AI-ETC</p>
              <p className="text-xs font-medium text-slate-500 dark:text-slate-400">Officer Workspace</p>
            </div>
          </div>
        </div>
        <div className="mt-3 px-3 sidebar-search-input">
          <Input label="Search" placeholder="Search..." start={<Icon icon="Search" />} />
        </div>
        <nav className="mt-2 space-y-1 px-3">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-sm dark:bg-[#24272E] dark:text-white dark:border-l-2 dark:border-indigo-500'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-[#9A9CA2] dark:hover:bg-[#18191C] dark:hover:text-white'
                }`
              }
            >
              {item.icon}
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className="border-t border-slate-200 dark:border-[#222328] px-4 py-3">
        <button
          onClick={toggleTheme}
          className="mb-3 flex w-full items-center justify-center gap-2 rounded-full border border-slate-200 bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 transition-all hover:bg-slate-200 dark:border-[#2C2E34] dark:bg-[#18191C] dark:text-slate-200 dark:hover:bg-[#222328] cursor-pointer shadow-2xs"
          title="Toggle Light/Dark Theme"
        >
          <Icon icon={theme === 'dark' ? 'MoonFill' : 'SunFill'} className="h-4 w-4 text-amber-500 dark:text-indigo-400" />
          <span>{theme === 'dark' ? 'Dark Mode' : 'Light Mode'}</span>
        </button>
        <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{displayName}</p>
        <p className="text-xs text-slate-500 dark:text-slate-400">{displayRole}</p>
        <button
          onClick={logout}
          className="mt-2 flex items-center gap-1.5 text-xs font-medium text-rose-600 hover:text-rose-700 dark:text-rose-400 dark:hover:text-rose-300 hover:underline cursor-pointer"
          title="Log out"
        >
          <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
          <span>Log keluar</span>
        </button>
      </div>
    </div>
  );
}

export function AppLayout({ title, subtitle, children }: AppLayoutProps) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex h-screen w-full bg-slate-50 text-slate-900 dark:bg-[#0D0D0F] dark:text-slate-100">
      {/* Desktop sidebar */}
      <aside className="hidden w-56 shrink-0 border-r border-slate-200 bg-white dark:border-[#222328] dark:bg-[#131417] md:block">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {mobileNavOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/40 dark:bg-black/60 backdrop-blur-xs transition-opacity"
            onClick={() => setMobileNavOpen(false)}
          />
          <div className="absolute left-0 top-0 h-full w-72 bg-white dark:bg-[#131417] shadow-xl transition-transform">
            <div className="flex justify-end border-b border-slate-200 dark:border-[#222328] p-2.5">
              <button
                onClick={() => setMobileNavOpen(false)}
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-[#222328]"
                aria-label="Close menu"
                title="Close menu"
              >
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="h-[calc(100%-45px)]">
              <SidebarContent onNavigate={() => setMobileNavOpen(false)} />
            </div>
          </div>
        </div>
      )}

      {/* Main area */}
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b border-slate-200 bg-white/80 dark:border-[#222328] dark:bg-[#131417]/80 backdrop-blur-md px-4 py-3 shadow-sm md:px-8">
          <div className="flex items-center gap-3">
            <button
              className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-[#222328] md:hidden"
              onClick={() => setMobileNavOpen(true)}
              title="Open menu"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div>
              <h1 className="text-base font-semibold text-slate-900 dark:text-white md:text-lg">{title}</h1>
              <p className="hidden text-xs text-slate-500 dark:text-slate-400 sm:block">{subtitle}</p>
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 md:p-8 app-main-glow">{children}</main>
      </div>
    </div>
  );
}
