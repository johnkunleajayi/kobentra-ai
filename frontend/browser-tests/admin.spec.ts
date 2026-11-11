import { test, expect, type Page } from "@playwright/test";

const business = {
  id: "fictional-business",
  name: "Fictional Admin Test Business",
  country: "Ghana",
  industry: "Food",
  owners: [{ id: "test-owner", email: "owner@example.invalid" }],
  registered_at: null,
  business_status: "not_recorded",
};
const dashboard = {
  users: 21,
  businesses: 1,
  workspaces: 1,
  assessment_statuses: { completed_verified: 1 },
  qualification: {
    self_reported_snapshots: 1,
    independent_verification: "not_implemented",
  },
};
async function session(page: Page, admin: boolean) {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: {
        id: "test-owner",
        email: "owner@example.invalid",
        authenticated: true,
        capabilities: { platform_admin: admin },
      },
    }),
  );
}
async function api(page: Page) {
  await page.route("**/api/admin/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/dashboard"))
      return route.fulfill({ json: dashboard });
    if (url.pathname.endsWith("/users")) {
      const page = Number(url.searchParams.get("page") || 1),
        q = url.searchParams.get("q");
      return route.fulfill({
        json: {
          total: q ? 0 : 21,
          page,
          page_size: 20,
          items: q
            ? []
            : [
                {
                  id: String(page),
                  email: `test${page}@example.invalid`,
                  created_at: null,
                  businesses: [
                    {
                      business_id: business.id,
                      name: business.name,
                      role: "owner",
                    },
                  ],
                },
              ],
        },
      });
    }
    if (url.pathname.endsWith("/businesses"))
      return route.fulfill({
        json: { items: [business], total: 1, page: 1, page_size: 20 },
      });
    return route.fulfill({
      json: {
        ...business,
        assessment_history_limit: 100,
        assessments: [],
        qualification: {
          readiness: {
            score: null,
            classification: null,
            provisional: true,
            version: "kobentra-readiness-v1",
          },
          completeness: { percent: 0 },
          confidence: { classification: "self_reported" },
          gaps: [],
        },
      },
    });
  });
}

test("ordinary and signed-out users cannot enter admin or see navigation", async ({
  page,
}) => {
  await session(page, false);
  let reads = 0;
  await page.route("**/api/admin/**", (route) => {
    reads++;
    return route.fulfill({ status: 403, json: {} });
  });
  await page.goto("/admin");
  await expect(
    page.getByRole("heading", { name: "Administration access restricted" }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Administration", exact: true }),
  ).toHaveCount(0);
  expect(reads).toBe(0);
  await page.unroute("**/api/auth/me");
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  await page.goto("/admin/users");
  await expect(page).toHaveURL(/\/signin$/);
});

test("owner dashboard, directory pagination and business details are read-only", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await session(page, true);
  await api(page);
  await page.goto("/admin");
  await expect(
    page.getByRole("link", { name: "Administration", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Registered users", { exact: true }),
  ).toBeVisible();
  await page.screenshot({ path: "../work/admin-desktop.png", fullPage: true });
  await page
    .getByRole("navigation", { name: "Administration navigation" })
    .getByRole("link", { name: "Users", exact: true })
    .click();
  await expect(
    page.getByText("test1@example.invalid", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByText("test2@example.invalid", { exact: true }),
  ).toBeVisible();
  await page.getByRole("link", { name: business.name, exact: true }).click();
  await expect(
    page.getByRole("heading", { name: business.name }),
  ).toBeVisible();
  await expect(
    page.getByText("No assessments recorded.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: /approve|verify|suspend|edit|delete/i }),
  ).toHaveCount(0);
  await page
    .getByRole("link", { name: "Business directory", exact: false })
    .click();
  await expect(page.getByRole("table")).toContainText("Not recorded");
});

test("mobile dark directory search, empty state and keyboard access", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await session(page, true);
  await api(page);
  await page.goto("/admin/users");
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await page.getByLabel("Search email", { exact: true }).fill("no-match");
  await page.getByLabel("Search email", { exact: true }).press("Enter");
  await expect(
    page.getByRole("heading", { name: "No users found" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(
    page.getByRole("link", { name: "Administration", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close navigation" }).click();
  await page.screenshot({
    path: "../work/admin-mobile-dark.png",
    fullPage: true,
  });
});

test("loading, denial error and retry remain safe even with frontend capability", async ({
  page,
}) => {
  await session(page, true);
  let release!: () => void,
    denied = true;
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/admin/dashboard", async (route) => {
    await gate;
    return denied
      ? route.fulfill({ status: 403, body: "private denied detail" })
      : route.fulfill({ json: dashboard });
  });
  await page.goto("/admin");
  await expect(page.getByRole("status")).toBeVisible();
  release();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByText("private denied detail")).toHaveCount(0);
  denied = false;
  await page.getByRole("button", { name: "Retry", exact: true }).click();
  await expect(
    page.getByText("Registered users", { exact: true }),
  ).toBeVisible();
});
