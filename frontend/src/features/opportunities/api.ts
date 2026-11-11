import { businessPath, jsonWrite, workspaceRequest } from "../workspace/api";

export type Stage = "exploring" | "conversation" | "closed";
export interface OpportunityInput {
  title: string;
  stage: Stage;
}
export interface Opportunity extends OpportunityInput {
  id: string;
  organization_id: string;
}
export const opportunitiesPath = (id: string) =>
  `${businessPath(id)}/opportunities`;
export const opportunityPath = (business: string, id: string) =>
  `${opportunitiesPath(business)}/${encodeURIComponent(id)}`;
export const createOpportunity = (business: string, input: OpportunityInput) =>
  workspaceRequest<Opportunity>(
    opportunitiesPath(business),
    jsonWrite("POST", input),
  );
export const updateOpportunity = (
  business: string,
  id: string,
  input: OpportunityInput,
) =>
  workspaceRequest<Opportunity>(
    opportunityPath(business, id),
    jsonWrite("PUT", input),
  );
