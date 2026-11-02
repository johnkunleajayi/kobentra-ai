export type Role = "owner" | "admin" | "member";
export interface BusinessProfile {
  name: string;
  sector: string;
  country: string;
  goal: string;
}
export interface Match {
  id: string;
  name: string;
  country: string;
  sector: string;
  kind: string;
  explanation: string;
  initials: string;
}
export interface Introduction {
  id: string;
  matchId: string;
  name: string;
  message: string;
  status: "requested" | "withdrawn";
}
export interface Opportunity {
  id: string;
  name: string;
  stage: "Exploring" | "In conversation" | "Closed";
}
export interface AuthProvider {
  status: "not_configured";
  signIn(email: string, password: string): Promise<never>;
}
export const emailProvider: AuthProvider = {
  status: "not_configured",
  async signIn() {
    throw new Error(
      "Email authentication is not configured. No account was created or session started.",
    );
  },
};
export const googleProvider = { status: "not_configured" as const };
export const integrationStatus = {
  salesforce: "not connected",
  eventspark: "planned",
} as const;
