import { UserManager, WebStorageStateStore, User } from 'oidc-client-ts';

function getDynamicKeycloakUrl(): string {
  const envUrl = import.meta.env.VITE_KEYCLOAK_URL;
  if (envUrl && !envUrl.includes('loca.lt')) {
    return envUrl;
  }
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:8080`;
}

const KEYCLOAK_URL = getDynamicKeycloakUrl();
const KEYCLOAK_REALM =
  import.meta.env.VITE_KEYCLOAK_REALM ?? 'mara-ai-etc';
const CLIENT_ID =
  import.meta.env.VITE_KEYCLOAK_CLIENT_ID ?? 'mara-officer-workspace';


// OIDC redirect goes to /callback — a dedicated page that handles the code
// exchange and then navigates to the original destination (or /).
const REDIRECT_URI = `${window.location.origin}/callback`;
const POST_LOGOUT_REDIRECT_URI = `${window.location.origin}/login`;

function createUserManager(): UserManager {
  return new UserManager({
    authority: `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}`,
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    post_logout_redirect_uri: POST_LOGOUT_REDIRECT_URI,
    response_type: 'code',
    scope: 'openid profile email roles',
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    automaticSilentRenew: true,
    // Store the original URL in OIDC state so CallbackPage can restore it
    // after a successful login (oidc-client-ts handles this transparently).
  });
}

let userManager: UserManager | null = null;

function getUserManager(): UserManager {
  if (!userManager) {
    userManager = createUserManager();
  }
  return userManager;
}

// ---------------------------------------------------------------------------
// User profile helpers
// ---------------------------------------------------------------------------

export interface UserProfile {
  subject: string;
  name: string;
  email: string;
  username: string;
  roles: string[];
  accessToken: string;
}

/** Extract a structured profile from the OIDC user object or mock session. */
export function extractProfile(user: User | MockUserShape): UserProfile {
  const profile = user.profile as Record<string, unknown>;
  const realmAccess = profile['realm_access'] as { roles?: string[] } | undefined;
  const roles =
    realmAccess?.roles ??
    (Array.isArray(profile['roles']) ? (profile['roles'] as string[]) : []);

  return {
    subject: (profile['sub'] as string) ?? '',
    name: (profile['name'] as string) ?? (profile['preferred_username'] as string) ?? '',
    email: (profile['email'] as string) ?? '',
    username: (profile['preferred_username'] as string) ?? '',
    roles,
    accessToken: user.access_token ?? '',
  };
}

// ---------------------------------------------------------------------------
// Mock / Dev Mode (dev builds only)
// ---------------------------------------------------------------------------

const MOCK_USER_STORAGE_KEY = 'mara_mock_auth_user';

interface MockUserShape {
  profile: Record<string, unknown>;
  access_token: string;
  expired: boolean;
  expires_at: number;
}

async function fetchBackendDevToken(): Promise<string | null> {
  try {
    const response = await fetch('/api/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'officer@mara.local',
        password: 'Officer123!',
      }),
    });
    if (!response.ok) return null;
    const body = (await response.json()) as { access_token?: string };
    return body.access_token ?? null;
  } catch {
    return null;
  }
}

/** Sign in using Mock / Dev Mode without Keycloak server. */
export async function loginMock(): Promise<void> {
  const backendToken = await fetchBackendDevToken();
  const mockUser: MockUserShape = {
    profile: {
      sub: 'mock-officer-001',
      name: 'Pegawai MARA (Dev Mode)',
      preferred_username: 'pegawai.mara',
      email: 'pegawai@mara.gov.my',
      roles: ['officer', 'reviewer', 'admin'],
    },
    access_token: backendToken ?? 'mock-jwt-token-dev-mode',
    expired: false,
    expires_at: Math.floor(Date.now() / 1000) + 86400,
  };
  window.sessionStorage.setItem(MOCK_USER_STORAGE_KEY, JSON.stringify(mockUser));
  window.location.assign(window.location.origin + '/');
}

// ---------------------------------------------------------------------------
// Real Keycloak OIDC flow
// ---------------------------------------------------------------------------

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

/** Log the user out and redirect to Keycloak logout endpoint. */
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
      const u = JSON.parse(mockJson) as MockUserShape;
      return u.access_token ?? null;
    } catch {
      // ignore invalid json
    }
  }

  const mgr = getUserManager();
  const user = await mgr.getUser();
  return user?.access_token ?? null;
}

/** Get the structured profile of the current user, or null if not logged in. */
export async function getUserProfile(): Promise<UserProfile | null> {
  const mockJson = window.sessionStorage.getItem(MOCK_USER_STORAGE_KEY);
  if (mockJson) {
    try {
      const u = JSON.parse(mockJson) as MockUserShape;
      return extractProfile(u);
    } catch {
      return null;
    }
  }

  const mgr = getUserManager();
  const user = await mgr.getUser();
  if (!user || user.expired) return null;
  return extractProfile(user);
}
