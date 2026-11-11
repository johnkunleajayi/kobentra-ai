import { test, expect } from "@playwright/test";
import { businesses, mockWorkspace } from "./workspace-fixture";

test("one-business selection redirects by stable organization ID", async ({
  page,
}) => {
  await mockWorkspace(page, businesses.slice(0, 1));
  await page.goto("/workspace");
  await expect(page).toHaveURL(/\/workspace\/org-a$/);
  await expect(page.getByLabel("Active business")).toHaveValue("org-a");
});

test("multi-business selection, preferences persistence and switching clear drafts", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await mockWorkspace(page);
  await page.goto("/workspace");
  await expect(
    page.getByRole("link", { name: "Open workspace", exact: true }),
  ).toHaveCount(2);
  await page
    .getByRole("link", { name: "Open workspace", exact: true })
    .first()
    .click();
  await page
    .getByRole("link", { name: "Market preferences", exact: true })
    .click();
  await page.getByRole("button", { name: "Add target market" }).click();
  await page.getByLabel("Country 1", { exact: true }).fill("Ghana");
  await page.getByLabel("Partner type 1", { exact: true }).fill("Distributor");
  await page.getByRole("button", { name: "Save preferences" }).click();
  await expect(page.getByRole("status")).toContainText("saved");
  await page.reload();
  await expect(page.getByLabel("Country 1", { exact: true })).toHaveValue(
    "Ghana",
  );
  await page.getByLabel("Country 1", { exact: true }).fill("Unsaved draft");
  await page.getByLabel("Active business").selectOption("org-b");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Sample Beta",
  );
  await page
    .getByRole("link", { name: "Market preferences", exact: true })
    .click();
  await expect(
    page.getByText("No target markets saved yet.", { exact: false }),
  ).toBeVisible();
  await expect(page.locator('input[value="Unsaved draft"]')).toHaveCount(0);
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
  await page.screenshot({
    path: "../work/workspace-mobile.png",
    fullPage: true,
  });
  await page.getByLabel("Active business").selectOption("org-a");
  await page
    .getByRole("link", { name: "Market preferences", exact: true })
    .click();
  await expect(page.getByLabel("Country 1", { exact: true })).toHaveValue(
    "Ghana",
  );
});

test("opportunity creation, detail, editing and tenant-scoped list", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await mockWorkspace(page);
  await page.goto("/workspace/org-a/opportunities");
  await expect(
    page.getByText("No opportunities have been created", { exact: false }),
  ).toBeVisible();
  await page.getByLabel("Opportunity title").fill("Seeking trade partners");
  await page
    .getByRole("button", { name: "Create opportunity", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Seeking trade partners" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Edit opportunity" }).click();
  await page
    .getByLabel("Opportunity title")
    .fill("Seeking distribution partners");
  await page.getByRole("combobox", { name: "Status", exact: true }).selectOption("conversation");
  await page
    .getByRole("button", { name: "Save opportunity", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("saved");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Seeking distribution partners" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await page.screenshot({
    path: "../work/workspace-opportunity-dark.png",
    fullPage: true,
  });
  await page.getByLabel("Active business").selectOption("org-b");
  await page.getByRole("link", { name: "Opportunities", exact: true }).click();
  await expect(
    page.getByText("No opportunities have been created", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Seeking distribution partners" }),
  ).toHaveCount(0);
});

test("unknown business fails closed without displaying private records", async ({
  page,
}) => {
  await mockWorkspace(page);
  await page.goto("/workspace/unknown/opportunities");
  await expect(page.getByRole("alert")).toContainText("unavailable");
  await expect(page.getByLabel("Active business")).toHaveCount(0);
});

test("member UI is read-only", async ({ page }) => {
  await mockWorkspace(page, [{ ...businesses[0], role: "member" }]);
  await page.goto("/workspace/org-a/opportunities");
  await expect(
    page.getByText("Your membership has read-only access."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create opportunity", exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("link", { name: "Market preferences", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Save preferences" }),
  ).toHaveCount(0);
});

test("late write response cannot switch the active business back", async ({
  page,
}) => {
  await mockWorkspace(page);
  let release = () => {};
  const gate = new Promise<void>((resolve) => {
    release = resolve;
  });
  await page.route("**/api/businesses/org-a/opportunities", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    await gate;
    await route.fulfill({
      status: 201,
      json: {
        id: "late",
        organization_id: "org-a",
        title: "Late",
        stage: "exploring",
      },
    });
  });
  await page.goto("/workspace/org-a/opportunities");
  await page.getByLabel("Opportunity title").fill("Late");
  await page
    .getByRole("button", { name: "Create opportunity", exact: true })
    .click();
  await expect(page.getByRole("button", { name: "Saving…" })).toBeVisible();
  await page.getByLabel("Active business").selectOption("org-b");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Sample Beta",
  );
  const response = page.waitForResponse(
    (r) =>
      r.url().includes("/org-a/opportunities") &&
      r.request().method() === "POST",
  );
  release();
  await (await response).finished();
  await page.evaluate(
    () =>
      new Promise((resolve) =>
        requestAnimationFrame(() => requestAnimationFrame(resolve)),
      ),
  );
  await expect(page).toHaveURL(/\/workspace\/org-b$/);
  await expect(
    page.getByRole("heading", { name: "Late", exact: true }),
  ).toHaveCount(0);
});
