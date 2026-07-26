import { UserManager, WebStorageStateStore, User } from 'oidc-client-ts';

const KEYCLOAK_URL =
  import.meta.env.VITE_KEYCLOAK_URL ?? 'http://localhost:8080';
const KEYCLOAK_REALM =
  import.meta.env.VITE_KEYCLOAK_REALM ?? 'mara-ai-etc';
const CLIENT_ID =
  import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'mara-officer-workspace';
const REDIRECT_URI = `${window.location.origin}/`;

function createUserManager(): UserManager {
  return new UserManager({
    authority: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}`,
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: 'openid profile email roles',
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    automaticSilentRenew: true,
  });
}

let userManager: UserManager | null = null;

function getUserManager(): UserManager {
  if (!userManager) {
    userManager = createUserManager();
  }
  return userManager;
}

const MOCK_USER_STORAGE_KEY = 'mara_mock_auth_user';

/** Sign in using Mock / Dev Mode without Keycloak server. */
export async function loginMock(): Promise<void> {
  const mockUser = {
    profile: {
      sub: 'mock-officer-001',
      name: 'Pegawai MARA (Dev Mode)',
      preferred_username: 'pegawai.mara',
      email: 'pegawai@mara.gov.my',
      roles: ['officer', 'reviewer', 'admin'],
    },
    access_token: 'mock-jwt-token-dev-mode',
    expired: false,
    expires_at: Math.floor(Date.now() / 1000) + 86400,
  };
  window.sessionStorage.setItem(MOCK_USER_STORAGE_KEY, JSON.stringify(mockUser));
  window.location.assign(window.location.origin + '/');
}

/** Redirect the browser to Keycloak SSO login page. */
export async function login(): Promise<void> {
  const mgr = getUserManager();
  await mgr.signinRedirect();
}

/** Handle the OIDC redirect callback and return the authenticated user. */
export async function handleRedirectCallback(): Promise<User | null> {
  const mgr = getUserManager();
  try {
    const user = await mgr.signinRedirectCallback();
    return user;
  } catch {
    return null;
  }
}

/** Log the user out and redirect to Keycloak. */
export async function logout(): Promise<void> {
  const mockJson = window.sessionStorage.getItem(MOCK_USER_STORAGE_KEY);
  if (mockJson) {
    window.sessionStorage.removeItem(MOCK_USER_STORAGE_KEY);
    window.location.assign(window.location.origin + '/login');
    return;
  }

  const mgr = getUserManager();
  await mgr.signoutRedirect();
}

/** Return the currently authenticated user, or null. */
export async function getUser(): Promise<User | null> {
  const mockJson = window.sessionStorage.getItem(MOCK_USER_STORAGE_KEY);
  if (mockJson) {
    try {
      return JSON.parse(mockJson) as User;
    } catch {
      // ignore invalid json
    }
  }

  const mgr = getUserManager();
  const user = await mgr.getUser();
  return user;
}

/** Get a Bearer token for API requests. */
export async function getAccessToken(): Promise<string | null> {
  const mockJson = window.sessionStorage.getItem(MOCK_USER_STORAGE_KEY);
  if (mockJson) {
    try {
      const u = JSON.parse(mockJson);
      return u.access_token ?? null;
    } catch {
      // ignore invalid json
    }
  }

  const mgr = getUserManager();
  const user = await mgr.getUser();
  return user?.access_token ?? null;
}
