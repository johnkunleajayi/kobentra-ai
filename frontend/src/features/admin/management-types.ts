export interface Administration {
  approval: "pending" | "approved" | "rejected";
  identity: "unverified" | "verified";
  access: "active" | "suspended";
  version: number;
}
export interface EditableProfile {
  name: string;
  sector: string;
  country: string;
  goal: string;
}
export type AdminAction =
  | "approve"
  | "reject"
  | "verify_identity"
  | "revoke_identity"
  | "suspend"
  | "reactivate"
  | "edit_profile";
export interface HistoryPage {
  total: number;
  page: number;
  page_size: number;
  items: {
    id: string;
    actor_id: string;
    action: string;
    reason: string;
    created_at: string;
    evidence_references: string[];
    previous_values: Record<string, unknown>;
    new_values: Record<string, unknown>;
  }[];
}
