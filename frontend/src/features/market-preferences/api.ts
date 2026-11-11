import { businessPath, jsonWrite, workspaceRequest } from "../workspace/api";

export interface Preference {
  country: string;
  partner_type: string;
}
export interface Preferences {
  preferences: Preference[];
}
export const preferencesPath = (businessId: string) =>
  `${businessPath(businessId)}/market-preferences`;
export const savePreferences = (
  businessId: string,
  preferences: Preference[],
) =>
  workspaceRequest<Preferences>(
    preferencesPath(businessId),
    jsonWrite("PUT", { preferences }),
  );
