import { businessPath, jsonWrite, workspaceRequest } from "../workspace/api";

export interface Assessment {
  id: string;
  organization_id: string;
  business_id: string;
  provider: string;
  assessment_type: string;
  provider_survey_id: string;
  provider_response_id: string | null;
  status: "initiated" | "launch_requested" | "completed_verified";
  initiated_at: string;
  completed_at: string | null;
  synchronized_at: string | null;
  integration_mode: "shared_public_link" | "salesforce_flow";
  salesforce_lead_id: string | null;
  dispatch_state: "sending" | "uncertain" | "sent" | null;
}
export interface AssessmentConfig {
  title: string;
  provider: string;
  configured: boolean;
  synchronization: "not_connected" | "salesforce_flow";
  unique_tracking_link: false;
}
export interface Launch {
  assessment: Assessment;
  launch_url: string;
  unique_tracking_link: false;
}
export const assessmentsPath = (business: string) =>
  `${businessPath(business)}/assessments`;
export const initiateAssessment = (business: string) =>
  workspaceRequest<Assessment>(
    assessmentsPath(business),
    jsonWrite("POST", {}),
  );
export const launchAssessment = (business: string, id: string) =>
  workspaceRequest<Launch>(
    `${assessmentsPath(business)}/${encodeURIComponent(id)}/launch`,
    jsonWrite("POST", {}),
  );
