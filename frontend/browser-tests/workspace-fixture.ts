import type { Page } from "@playwright/test";
import type { Business } from "../src/features/business/types";
import type { Preferences } from "../src/features/market-preferences/api";
import type { Opportunity } from "../src/features/opportunities/api";

export const businesses: Business[] = [
  {
    organization_id: "org-a",
    profile_id: "profile-a",
    name: "Sample Alpha",
    sector: "Trade",
    country: "Ghana",
    goal: "Find buyers",
    role: "owner",
  },
  {
    organization_id: "org-b",
    profile_id: "profile-b",
    name: "Sample Beta",
    sector: "Food",
    country: "Senegal",
    goal: "Find suppliers",
    role: "owner",
  },
];
export async function mockWorkspace(page: Page, allowed = businesses) {
  const preferences: Record<string, Preferences> = Object.fromEntries(
    allowed.map((b) => [b.organization_id, { preferences: [] }]),
  );
  const opportunities: Record<string, Opportunity[]> = Object.fromEntries(
    allowed.map((b) => [b.organization_id, []]),
  );
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: {
        id: "sample-user",
        email: "sample@example.invalid",
        authenticated: true,
      },
    }),
  );
  await page.route("**/api/businesses**", async (route) => {
    const parts = new URL(route.request().url()).pathname
      .split("/")
      .filter(Boolean);
    const [, , id, feature, recordId] = parts;
    if (!id) return route.fulfill({ json: { businesses: allowed } });
    const business = allowed.find((b) => b.organization_id === id);
    if (!business)
      return route.fulfill({
        status: 403,
        json: { error: { code: "access_denied" } },
      });
    if (!feature) return route.fulfill({ json: business });
    const method = route.request().method();
    if (feature === "market-preferences") {
      if (method === "PUT") preferences[id] = route.request().postDataJSON();
      return route.fulfill({ json: preferences[id] });
    }
    if (feature === "opportunities") {
      if (method === "POST") {
        const row = {
          ...route.request().postDataJSON(),
          id: `opp-${opportunities[id].length + 1}`,
          organization_id: id,
        } as Opportunity;
        opportunities[id].push(row);
        return route.fulfill({ status: 201, json: row });
      }
      if (recordId) {
        const row = opportunities[id].find((o) => o.id === recordId);
        if (!row) return route.fulfill({ status: 404, json: {} });
        if (method === "PUT")
          Object.assign(row, route.request().postDataJSON());
        return route.fulfill({ json: row });
      }
      return route.fulfill({ json: { opportunities: opportunities[id] } });
    }
    return route.fulfill({ status: 404, json: {} });
  });
  return { preferences, opportunities };
}
