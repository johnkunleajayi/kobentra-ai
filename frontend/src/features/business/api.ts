import { API_BASE } from "../auth/session";
import type { Business, BusinessInput } from "./types";

export class BusinessApiError extends Error {
  constructor(public status: number) {
    super(
      status === 401
        ? "Your session has expired. Please sign in again."
        : status === 422
          ? "Check the required fields and their length limits."
          : status === 403
            ? "This request was blocked. Refresh and try again."
            : "Business information is unavailable. Please try again.",
    );
  }
}

async function request(options?: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE}/api/businesses`, {
    ...options,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) throw new BusinessApiError(response.status);
  return response;
}

export async function listBusinesses(): Promise<Business[]> {
  const response = await request();
  const data: { businesses: Business[] } = await response.json();
  return data.businesses;
}

export async function registerBusiness(
  input: BusinessInput,
): Promise<Business> {
  const response = await request({
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return response.json();
}
