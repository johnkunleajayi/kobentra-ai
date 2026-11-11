export interface AuthenticatedUser {
  id: string;
  email: string;
  authenticated: true;
  capabilities?: { platform_admin: boolean };
}

export const API_BASE = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8002"
).replace(/\/$/, "");

export function startGoogleLogin(): void {
  window.location.assign(`${API_BASE}/api/auth/google/login`);
}

export async function getCurrentUser(): Promise<AuthenticatedUser | null> {
  const response = await fetch(`${API_BASE}/api/auth/me`, {
    credentials: "include",
    cache: "no-store",
  });

  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Unable to check your session.");

  const user: AuthenticatedUser = await response.json();
  return user;
}

export async function signOut(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });

  if (!response.ok) throw new Error("Unable to sign out.");
}
