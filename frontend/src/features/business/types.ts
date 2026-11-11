export interface BusinessInput {
  name: string;
  sector: string;
  country: string;
  goal: string;
}
export interface Business extends BusinessInput {
  organization_id: string;
  profile_id: string;
  role: string;
}
