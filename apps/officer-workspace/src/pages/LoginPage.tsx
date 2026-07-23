import { login } from '../services/auth';

export function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="w-full max-w-md space-y-6 rounded-lg bg-white p-8 shadow-md">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-gray-900">
            MARA AI-ETC
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            Officer Workspace
          </p>
        </div>

        <p className="text-center text-sm text-gray-500">
          Sign in with your MARA corporate account to access the
          AI Entrepreneurship Transformation Centre.
        </p>

        <button
          onClick={login}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white
                     transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2
                     focus:ring-blue-500 focus:ring-offset-2"
        >
          Sign in with SSO (Keycloak)
        </button>

        <p className="text-center text-xs text-gray-400">
          Powered by MARA AI-ETC — Milestone 0
        </p>
      </div>
    </div>
  );
}
