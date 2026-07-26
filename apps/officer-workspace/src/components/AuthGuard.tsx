import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { getUser } from '../services/auth';
import { isDevMode } from '../services/dev-auth';

interface AuthGuardProps {
  children: ReactNode;
}

/**
 * Route guard that ensures an authenticated Keycloak session exists before
 * rendering protected pages.
 *
 * - OIDC callback handling (code + state exchange) is now done exclusively in
 *   <CallbackPage /> at /callback — not here.
 * - In development (import.meta.env.DEV), also accepts a dev-mode session set
 *   by the LoginPage "Dev Mode" button.
 * - If no valid session is found, redirects to /login.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);
  const ran = useRef(false);

  useEffect(() => {
    // Guard against StrictMode double-invoke
    if (ran.current) return;
    ran.current = true;

    async function check() {
      // Dev mode bypass (local dev only — tree-shaken in prod)
      if (import.meta.env.DEV && isDevMode()) {
        setAuthenticated(true);
        setChecking(false);
        return;
      }

      // Normal auth check — getUser() reads from oidc-client-ts sessionStorage
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
      <div className="flex h-screen items-center justify-center bg-white">
        <div className="flex flex-col items-center gap-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-700 border-t-transparent" />
          <p className="text-sm text-slate-500">Mengesahkan sesi…</p>
        </div>
      </div>
    );
  }

  if (!authenticated) {
    // Will be redirected to /login by the effect above; render nothing
    return null;
  }

  return <>{children}</>;
}
