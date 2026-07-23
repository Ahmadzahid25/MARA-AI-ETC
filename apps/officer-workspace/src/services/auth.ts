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
  const mgr = getUserManager();
  await mgr.signoutRedirect();
}

/** Return the currently authenticated user, or null. */
export async function getUser(): Promise<User | null> {
  const mgr = getUserManager();
  const user = await mgr.getUser();
  return user;
}

/** Get a Bearer token for API requests. */
export async function getAccessToken(): Promise<string | null> {
  const mgr = getUserManager();
  const user = await mgr.getUser();
  return user?.access_token ?? null;
}
