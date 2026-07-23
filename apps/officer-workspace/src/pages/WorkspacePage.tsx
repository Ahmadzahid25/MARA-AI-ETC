import { useEffect, useState } from 'react';
import { getUser, logout, getAccessToken } from '../services/auth';

interface UserProfile {
  name: string;
  email: string;
  roles: string[];
}

export function WorkspacePage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      const user = await getUser();
      if (user) {
        setProfile({
          name: user.profile?.name ?? user.profile?.preferred_username ?? 'Officer',
          email: user.profile?.email ?? '',
          roles: (user.profile?.roles as string[] | undefined) ?? [],
        });
      }
      setLoading(false);
    }

    load();
  }, []);

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">Loading workspace…</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between border-b bg-white px-6 py-3 shadow-sm">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">
            MARA AI-ETC
          </h1>
          <p className="text-xs text-gray-500">Officer Workspace</p>
        </div>
        <div className="flex items-center gap-4">
          {profile && (
            <span className="text-sm text-gray-600">{profile.name}</span>
          )}
          <button
            onClick={logout}
            className="rounded-md bg-gray-100 px-3 py-1.5 text-sm text-gray-700
                       transition-colors hover:bg-gray-200"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Main content */}
      <div className="flex flex-1">
        {/* Sidebar placeholder */}
        <aside className="w-56 border-r bg-white p-4">
          <nav className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wide text-gray-400">
              Navigation
            </p>
            <div className="rounded-md bg-blue-50 px-3 py-2 text-sm font-medium text-blue-700">
              Dashboard
            </div>
            <div className="rounded-md px-3 py-2 text-sm text-gray-500">
              Applications
            </div>
            <div className="rounded-md px-3 py-2 text-sm text-gray-500">
              Reports
            </div>
          </nav>
        </aside>

        {/* Content area */}
        <main className="flex flex-1 items-center justify-center p-8">
          <div className="max-w-md text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-blue-100">
              <span className="text-2xl text-blue-600">!</span>
            </div>
            <h2 className="mb-2 text-xl font-semibold text-gray-900">
              Welcome, {profile?.name ?? 'Officer'}
            </h2>
            <p className="mb-4 text-gray-500">
              Your workspace is ready. No agents are available yet — agent
              features will arrive in Milestone 1 and beyond.
            </p>
            <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <p className="font-medium">Milestone 0 — Foundation</p>
              <p className="mt-1">
                Authentication and core infrastructure are operational.
                Agent capabilities are under development.
              </p>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
