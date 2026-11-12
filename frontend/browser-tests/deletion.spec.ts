import { test, expect, type Page } from "@playwright/test";

const name = "Fictional deletion fixture";
const id = "00000000-0000-4000-8000-000000000002";
async function mock(page: Page, pending = false, recycled = false) {
  const writes: Record<string, unknown>[] = [];
  const operation = {
    id: "00000000-0000-4000-8000-000000000001",
    state: "local_pending",
    local_data_removed: false,
    completed_at: null as string | null,
    error_code: null,
    salesforce_outcome: recycled ? "recycled_verified" : "not_linked",
    events: [],
  };
  let current: typeof operation | null = pending ? operation : null;
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({
      json: {
        id: "owner",
        email: "owner@example.invalid",
        authenticated: true,
        capabilities: { platform_admin: true },
      },
    }),
  );
  await page.route("**/api/admin/businesses/**", (route) => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith("/deletion/preview"))
      return route.fulfill({
        json: {
          business_name: name,
          version: 0,
          preview_token: "a".repeat(64),
          dependencies: { business_profiles: 1, memberships: 1 },
          salesforce_target: null,
          implications: ["Required audit history is retained."],
          salesforce_deletion_enabled: false,
          salesforce_deletion_policy: "recycle_bin",
        },
      });
    if (path.endsWith("/deletion") || path.endsWith("/deletion/retry")) {
      if (route.request().method() === "POST") {
        writes.push(route.request().postDataJSON());
        current = {
          ...operation,
          state: "completed",
          local_data_removed: true,
          completed_at: "2026-11-11T12:00:00Z",
        };
      }
      return route.fulfill({ json: { operation: current } });
    }
    if (path.endsWith("/history"))
      return route.fulfill({
        json: { total: 0, items: [], page: 1, page_size: 20 },
      });
    return route.fulfill({
      json: {
        id,
        name,
        country: "Ghana",
        industry: "Food",
        owners: [],
        registered_at: null,
        business_status: "not_recorded",
        administration: {
          approval: "pending",
          identity: "unverified",
          access: "active",
          version: 0,
        },
        profile: {
          name,
          sector: "Food",
          country: "Ghana",
          goal: "Fictional goal",
        },
        assessments: [],
        assessment_history_limit: 100,
        qualification: {
          readiness: { score: null, classification: null },
          confidence: { classification: "self_reported" },
          completeness: { percent: 0 },
          gaps: [],
        },
      },
    });
  });
  return writes;
}

test("deletion preview, exact name, reason and cancellation before local completion", async ({
  page,
}) => {
  const writes = await mock(page);
  await page.goto(`/admin/businesses/${id}`);
  await page
    .getByRole("button", { name: "Delete business", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await expect(
    dialog.getByText("business profiles", { exact: true }),
  ).toBeVisible();
  await dialog.getByLabel("Type the business name exactly").fill("Wrong");
  await dialog
    .getByLabel("Required deletion reason")
    .fill("Remove fictional fixture");
  await dialog
    .getByRole("button", { name: "Confirm business deletion" })
    .click();
  await expect(dialog.getByRole("alert")).toContainText("exact business name");
  expect(writes).toHaveLength(0);
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await page
    .getByRole("button", { name: "Delete business", exact: true })
    .click();
  await dialog.getByLabel("Type the business name exactly").fill(name);
  await dialog
    .getByLabel("Required deletion reason")
    .fill("Remove fictional fixture");
  await dialog
    .getByRole("button", { name: "Confirm business deletion" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Business deletion completed" }),
  ).toBeVisible();
  expect(writes).toHaveLength(1);
  expect(writes[0].business_name).toBe(name);
  expect(writes[0].expected_version).toBe(0);
  expect(writes[0]).not.toHaveProperty("actor_id");
  expect(writes[0]).not.toHaveProperty("salesforce_lead_id");
});

test("linked Recycle Bin deletion can be confirmed on mobile", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const writes = await mock(page, false, true);
  await page.route("**/deletion/preview", (route) =>
    route.fulfill({
      json: {
        business_name: name,
        version: 0,
        preview_token: "a".repeat(64),
        dependencies: { business_profiles: 1 },
        salesforce_target: {
          lead_id: "00Q000000000001AAA",
          org_id: "00D000000000001AAA",
          origin: "https://sample.my.salesforce.com",
        },
        implications: [
          "The linked Lead will move to the Salesforce Recycle Bin.",
        ],
        salesforce_deletion_enabled: true,
        salesforce_deletion_policy: "recycle_bin",
      },
    }),
  );
  await page.goto(`/admin/businesses/${id}`);
  await page
    .getByRole("button", { name: "Delete business", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toContainText(
    "recoverable Salesforce Recycle Bin",
  );
  await expect(
    page.getByRole("button", { name: "Confirm business deletion" }),
  ).toBeEnabled();
  expect(writes).toHaveLength(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "../work/admin-deletion-mobile.png",
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await page.getByRole("button", { name: "Delete business", exact: true }).click();
  await page.getByLabel("Type the business name exactly").fill(name);
  await page.getByLabel("Required deletion reason").fill("Recycle fictional linked Lead and remove local data");
  await page.getByRole("button", { name: "Confirm business deletion" }).click();
  await expect(page.getByRole("heading", { name: "Business deletion completed" })).toBeVisible();
  expect(writes).toHaveLength(1);
});

test("pending deletion blocks other decisions and safely resumes the original operation", async ({
  page,
}) => {
  const writes = await mock(page, true);
  await page.goto(`/admin/businesses/${id}`);
  await expect(
    page.getByRole("button", { name: "Approve", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByText(
      "Local data retained. Normal business operations are blocked.",
      { exact: true },
    ),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Resume deletion", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Business deletion completed" }),
  ).toBeVisible();
  expect(writes[0]).toEqual({
    operation_id: "00000000-0000-4000-8000-000000000001",
  });
});

test("lost confirmation response retrieves durable status instead of claiming completion", async ({
  page,
}) => {
  await mock(page);
  let uncertain = false;
  await page.route("**/deletion", (route) => {
    if (route.request().method() === "POST") {
      uncertain = true;
      return route.fulfill({ status: 503, json: {} });
    }
    if (uncertain)
      return route.fulfill({
        json: {
          operation: {
            id: "00000000-0000-4000-8000-000000000001",
            state: "local_pending",
            local_data_removed: false,
            completed_at: null,
            error_code: null,
            salesforce_outcome: "not_linked",
            events: [],
          },
        },
      });
    return route.fallback();
  });
  await page.goto(`/admin/businesses/${id}`);
  await page
    .getByRole("button", { name: "Delete business", exact: true })
    .click();
  await page.getByLabel("Type the business name exactly").fill(name);
  await page
    .getByLabel("Required deletion reason")
    .fill("Fictional recovery example");
  await page.getByRole("button", { name: "Confirm business deletion" }).click();
  await expect(page.getByRole("dialog").getByRole("alert")).toContainText(
    "not confirmed",
  );
  await page
    .getByRole("button", { name: "Check deletion status", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Resume deletion", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Approve", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("heading", { name: "Business deletion completed" }),
  ).toHaveCount(0);
});
