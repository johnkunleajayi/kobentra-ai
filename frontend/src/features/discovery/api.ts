import { businessPath } from "../workspace/api";
export const discoveryPath = (businessId: string) =>
  `${businessPath(businessId)}/matches`;
