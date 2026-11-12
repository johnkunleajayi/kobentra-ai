export interface DeletionPreview {
  business_name: string;
  version: number;
  preview_token: string;
  dependencies: Record<string, number>;
  implications: string[];
  salesforce_target: { lead_id: string; org_id: string; origin: string } | null;
  salesforce_deletion_enabled: boolean;
  salesforce_deletion_policy: "recycle_bin";
}
export interface DeletionStatus {
  operation: null | {
    id: string;
    state: string;
    error_code: string | null;
    local_data_removed: boolean;
    completed_at: string | null;
    salesforce_outcome: string;
    events: { state: string; created_at: string; error_code: string | null }[];
  };
}
