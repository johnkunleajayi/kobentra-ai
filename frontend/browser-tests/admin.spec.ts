import { test, expect, type Page } from "@playwright/test";

const business = {
  id: "fictional-business",
  name: "Fictional Admin Test Business",
  country: "Ghana",
  industry: "Food",
  owners: [{ id: "test-owner", email: "owner@example.invalid" }],
  registered_at: null,
  business_status: "not_recorded",
  administration: {
    approval: "pending",
    identity: "unverified",
    access: "active",
    version: 0,
  },
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
  let record = structuredClone(business);
  let profile = {
    name: business.name,
    country: business.country,
    sector: business.industry,
    goal: "Fictional test business goal",
  };
  const writes: Record<string, unknown>[] = [];
  const history: Record<string, unknown>[] = [];
  await page.route("**/api/admin/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/history"))
      return route.fulfill({
        json: { items: history, total: history.length, page: 1, page_size: 20 },
      });
    if (["POST", "PUT"].includes(route.request().method())) {
      const body = route.request().postDataJSON();
      writes.push(body);
      const previous = structuredClone(record.administration);
      if (body.profile) {
        profile = body.profile;
        record = {
          ...record,
          name: profile.name,
          country: profile.country,
          industry: profile.sector,
        };
        record.administration.identity = "unverified";
        record.administration.approval = "pending";
      } else {
        const changes: Record<
          string,
          ["approval" | "identity" | "access", string]
        > = {
          approve: ["approval", "approved"],
          reject: ["approval", "rejected"],
          verify_identity: ["identity", "verified"],
          revoke_identity: ["identity", "unverified"],
          suspend: ["access", "suspended"],
          reactivate: ["access", "active"],
        };
        const [key, value] = changes[body.action];
        record.administration[key] = value;
      }
      record.administration.version++;
      history.unshift({
        id: String(writes.length),
        actor_id: "test-owner",
        action: body.action || "edit_profile",
        reason: body.reason,
        created_at: "2026-11-11T12:00:00Z",
        evidence_references: body.evidence_references || [],
        previous_values: previous,
        new_values: structuredClone(record.administration),
      });
      return route.fulfill({
        json: {
          decision_id: String(writes.length),
          version: record.administration.version,
          replayed: false,
        },
      });
    }
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
        json: { items: [record], total: 1, page: 1, page_size: 20 },
      });
    return route.fulfill({
      json: {
        ...record,
        profile,
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
  return { writes };
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
    page.getByRole("button", { name: "Suspend", exact: true }),
  ).toBeEnabled();
  await expect(
    page.getByRole("button", { name: "Delete business", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Business directory", exact: false })
    .click();
  await expect(page.getByRole("table")).toContainText("pending");
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

test("administrative dialogs require reasons, record decisions and edit supported fields", async ({
  page,
}) => {
  await session(page, true);
  const mock = await api(page);
  await page.goto(`/admin/businesses/${business.id}`);
  await page.getByRole("button", { name: "Suspend", exact: true }).click();
  await page
    .getByRole("button", { name: "Confirm decision", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(mock.writes.length).toBe(0);
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  for (const label of [
    "Verify identity",
    "Suspend",
    "Reactivate",
    "Revoke verification",
  ]) {
    await page.getByRole("button", { name: label, exact: true }).click();
    const dialog = page.getByRole("dialog");
    await dialog
      .getByLabel("Required decision reason")
      .fill(`Fictional browser review: ${label}`);
    if (label === "Verify identity")
      await dialog
        .getByLabel("Independent evidence references (one per line)")
        .fill("local-review:fictional-example");
    await dialog.getByRole("button", { name: "Confirm decision" }).click();
    await expect(
      page.getByText("Administrative decision saved.", { exact: true }),
    ).toBeVisible();
  }
  await page
    .getByRole("button", { name: "Edit business", exact: true })
    .click();
  await page
    .getByLabel("Business name", { exact: true })
    .fill("Fictional Updated Business");
  await page
    .getByLabel("Business description / goal", { exact: true })
    .fill("Fictional updated description");
  await page
    .getByLabel("Required decision reason")
    .fill("Correct fictional profile");
  await page
    .getByRole("button", { name: "Confirm decision", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Fictional Updated Business" }),
  ).toBeVisible();
  expect(mock.writes.length).toBe(5);
  await expect(page.getByLabel("Administrative statuses")).toContainText(
    "Approval: pending",
  );
  await expect(
    page.getByRole("heading", { name: "Administrative decision history" }),
  ).toBeVisible();
  await expect(
    page.getByText("Correct fictional profile", { exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await page
    .getByRole("button", { name: "Verify identity", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../work/admin-management-mobile.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("failed decision preserves a safe identical retry", async ({ page }) => {
  await session(page, true);
  await api(page);
  const ids: string[] = [];
  await page.route("**/api/admin/businesses/*/decisions", (route) => {
    ids.push(route.request().postDataJSON().request_id);
    return ids.length === 1
      ? route.fulfill({ status: 503, body: "private write error" })
      : route.fallback();
  });
  await page.goto(`/admin/businesses/${business.id}`);
  await page.getByRole("button", { name: "Suspend", exact: true }).click();
  await page
    .getByLabel("Required decision reason")
    .fill("Retry fictional decision");
  await page
    .getByRole("button", { name: "Confirm decision", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "Decision was not confirmed",
  );
  await expect(page.getByText("private write error")).toHaveCount(0);
  await page
    .getByRole("button", { name: "Confirm decision", exact: true })
    .click();
  await expect(
    page.getByText("Administrative decision saved.", { exact: true }),
  ).toBeVisible();
  expect(ids).toHaveLength(2);
  expect(ids[0]).toBe(ids[1]);
});
