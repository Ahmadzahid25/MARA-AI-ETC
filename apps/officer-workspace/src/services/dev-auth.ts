/**
 * DEV MODE AUTH — for local development without a running Keycloak.
 * Sets a fake session token in sessionStorage that AuthGuard will accept.
 * NOT safe for production; tree-shaken in prod builds via import.meta.env.DEV.
 */

const DEV_USER_KEY = 'mara_dev_mode_user';

export interface DevUser {
  name: string;
  email: string;
  role: string;
}

const DEV_USER: DevUser = {
  name: 'Officer Zahid (Dev)',
  email: 'zahid@mara.gov.my',
  role: 'officer',
};

export function enableDevMode(): void {
  sessionStorage.setItem(DEV_USER_KEY, JSON.stringify(DEV_USER));
}

export function disableDevMode(): void {
  sessionStorage.removeItem(DEV_USER_KEY);
}

export function getDevUser(): DevUser | null {
  try {
    const raw = sessionStorage.getItem(DEV_USER_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as DevUser;
  } catch {
    return null;
  }
}

export function isDevMode(): boolean {
  return getDevUser() !== null;
}
