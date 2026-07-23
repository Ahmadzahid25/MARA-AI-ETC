import { useEffect, useState, type ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { getUser, handleRedirectCallback } from '../services/auth';

interface AuthGuardProps {
  children: ReactNode;
}

/**
 * Route guard that checks for an authenticated Keycloak session.
 * If the URL contains OIDC callback parameters, handles the callback first.
 * If no authenticated user is found, redirects to /login.
 */
export function AuthGuard({ children }: AuthGuardProps) {
  const navigate = useNavigate();
  const [checking, setChecking] = useState(true);
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    async function check() {
      // Check if this is an OIDC redirect (has code/state params)
      const params = new URLSearchParams(window.location.search);
      const isCallback = params.has('code') || params.has('state');

      if (isCallback) {
        const user = await handleRedirectCallback();
        if (user) {
          // Redirect to clean URL without OIDC params
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
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">Authenticating…</p>
      </div>
    );
  }

  if (!authenticated) {
    return null;
  }

  return <>{children}</>;
}
