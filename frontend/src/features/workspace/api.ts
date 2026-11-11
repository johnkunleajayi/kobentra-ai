import { API_BASE } from "../auth/session";

export async function workspaceRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok)
    throw new Error(
      response.status === 401
        ? "Your session has expired. Sign in again."
        : response.status === 403 || response.status === 404
          ? "This workspace or record is unavailable to your account."
          : response.status === 422
            ? "Check the required fields, lengths and duplicate entries."
            : "Unable to complete this request. Please retry.",
    );
  return response.json() as Promise<T>;
}
export const businessPath = (id: string) =>
  `/api/businesses/${encodeURIComponent(id)}`;
export const jsonWrite = (
  method: "POST" | "PUT",
  value: unknown,
): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(value),
});
