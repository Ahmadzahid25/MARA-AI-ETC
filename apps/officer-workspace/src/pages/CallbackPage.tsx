import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router';
import { handleRedirectCallback } from '../services/auth';

/**
 * Dedicated OIDC redirect-callback page.
 *
 * Keycloak redirects the browser here (at /callback?code=…&state=…) after a
 * successful login. This page:
 *   1. Calls handleRedirectCallback() to exchange the auth code for tokens.
 *   2. On success — navigates to the destination the user originally requested
 *      (stored in OIDC state) or falls back to "/".
 *   3. On failure — shows a clear error message with a "Try again" link.
 *
 * The route must be registered in App.tsx AND in Keycloak's redirectUris list
 * for the mara-officer-workspace client.
 */
export function CallbackPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const handled = useRef(false);

  useEffect(() => {
    // Guard against StrictMode double-invoke
    if (handled.current) return;
    handled.current = true;

    async function processCallback() {
      try {
        const user = await handleRedirectCallback();
        if (user) {
          // Navigate to the original destination (oidc-client-ts restores it
          // from the state parameter) or fall back to workspace root.
          navigate('/', { replace: true });
        } else {
          setError('Sesi log masuk tidak berjaya. Token tidak diterima daripada pelayan.');
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(`Ralat semasa memproses log masuk: ${msg}`);
      }
    }

    processCallback();
  }, [navigate]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-white px-6">
        <div className="w-full max-w-md rounded-xl border border-red-100 bg-red-50 p-8 text-center shadow-sm">
          {/* Error icon */}
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <svg
              className="h-6 w-6 text-red-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
          </div>

          <h1 className="text-lg font-semibold text-red-900">Log masuk gagal</h1>
          <p className="mt-2 text-sm text-red-700">{error}</p>

          <div className="mt-6 flex flex-col gap-2">
            <a
              href="/login"
              className="inline-flex w-full items-center justify-center rounded-lg bg-emerald-800 px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-emerald-900"
            >
              Cuba semula
            </a>
            <p className="text-xs text-red-500">
              Jika masalah berterusan, hubungi pentadbir sistem.
            </p>
          </div>
        </div>
      </div>
    );
  }

  // Loading state while processing the callback
  return (
    <div className="flex min-h-screen items-center justify-center bg-white">
      <div className="flex flex-col items-center gap-4">
        <div className="h-10 w-10 animate-spin rounded-full border-4 border-emerald-700 border-t-transparent" />
        <div className="text-center">
          <p className="text-sm font-medium text-slate-700">Mengesahkan sesi…</p>
          <p className="mt-1 text-xs text-slate-400">
            Sedang memproses log masuk SSO. Sila tunggu sebentar.
          </p>
        </div>
      </div>
    </div>
  );
}
