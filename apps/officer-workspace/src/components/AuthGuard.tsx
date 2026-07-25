import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { getUser, handleRedirectCallback } from '../services/auth';
import { isDevMode } from '../services/dev-auth';

interface AuthGuardProps {
  children: ReactNode;
}

/**
 * Route guard that checks for an authenticated Keycloak session.
 * In development (import.meta.env.DEV), also accepts a dev-mode session
 * set by the LoginPage "Dev Mode" button.
 * If no authenticated user is found, redirects to /login.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    async function check() {
      // Dev mode bypass (local dev only)
      if (import.meta.env.DEV && isDevMode()) {
        setAuthenticated(true);
        setChecking(false);
        return;
      }

      // Check if this is an OIDC redirect (has code/state params)
      const params = new URLSearchParams(window.location.search);
      const isCallback = params.has('code') || params.has('state');

      if (isCallback) {
        const user = await handleRedirectCallback();
        if (user) {
          window.location.replace(window.location.origin + '/');
          return;
        }
      }

      // Normal auth check
      const user = await getUser();
      if (user && !user.expired) {
        setAuthenticated(true);
      } else {
        navigate('/login', { replace: true });
      }

      setChecking(false);
    }

    check();
  }, [navigate]);

  if (checking) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0a0f1e]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-[#2563eb] border-t-transparent" />
          <p className="text-sm text-slate-400">Authenticating…</p>
        </div>
      </div>
    );
  }

  if (!authenticated) {
    return null;
  }

  return <>{children}</>;
}
