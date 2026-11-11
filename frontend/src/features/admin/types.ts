export interface AdminUser {
  id: string;
  email: string;
  created_at: string | null;
  businesses: { business_id: string; name: string; role: string }[];
}
export interface AdminBusiness {
  id: string;
  name: string;
  country: string;
  industry: string;
  registered_at: string | null;
  business_status: string;
  owners: { id: string; email: string }[];
}
export interface AdminPage<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface Dashboard {
  users: number;
  businesses: number;
  workspaces: number;
  assessment_statuses: Record<string, number>;
  qualification: {
    self_reported_snapshots: number;
    independent_verification: string;
  };
}
export interface BusinessDetail extends AdminBusiness {
  assessment_history_limit: number;
  assessments: {
    id: string;
    status: string;
    initiated_at: string;
    completed_at: string | null;
    provider: string;
  }[];
  qualification: {
    readiness: {
      score: number | null;
      classification: string | null;
      version: string;
      provisional: boolean;
    };
    confidence: { classification: string };
    completeness: { percent: number };
    gaps: { code: string; recommendation: string }[];
  };
}
export const dateLabel = (value: string | null) =>
  value ? new Date(value).toLocaleDateString() : "Not recorded";
