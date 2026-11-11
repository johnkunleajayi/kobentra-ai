import { test, expect } from "@playwright/test";

const sample = {
  organization_id: "sample-org",
  profile_id: "sample-profile",
  role: "owner",
  name: "Sample Cocoa",
  sector: "Food",
  country: "Ghana",
  goal: "Find buyers",
};

test("signed-out onboarding offers existing Google login", async ({ page }) => {
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({ status: 401, json: {} }),
  );
  await page.goto("/business/onboarding");
  await expect(
    page.getByRole("button", { name: "Continue with Google" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Register business", exact: true }),
  ).toHaveCount(0);
});

test("onboarding saves through API and account reload retrieves persisted response", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({
      json: {
        id: "sample-user",
        email: "sample@example.invalid",
        authenticated: true,
      },
    }),
  );
  let saved = false;
  await page.route("**/api/businesses", async (r) => {
    if (r.request().method() === "POST") {
      expect(r.request().postDataJSON()).toEqual({
        name: sample.name,
        sector: sample.sector,
        country: sample.country,
        goal: sample.goal,
      });
      saved = true;
      await r.fulfill({ status: 201, json: sample });
    } else await r.fulfill({ json: { businesses: saved ? [sample] : [] } });
  });
  await page.goto("/account");
  await page
    .getByRole("link", { name: "Register your business", exact: true })
    .click();
  await page.getByLabel("Business name").fill(" Sample Cocoa ");
  await page.getByLabel("Business sector").fill("Food");
  await page.getByLabel("Primary country or market").fill("Ghana");
  await page.getByLabel("Business goal").fill("Find buyers");
  await page.screenshot({
    path: "../work/business-onboarding-mobile.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Register business", exact: true })
    .click();
  await expect(page.getByText("Your business registration has been saved.")).toBeVisible();
  await expect(page.getByRole("heading", { name: sample.name })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: sample.name })).toBeVisible();
  expect(
    await page.evaluate(() => sessionStorage.getItem("kobentra-demo-profile")),
  ).toBeNull();
  await page.screenshot({
    path: "../work/business-account-mobile.png",
    fullPage: true,
  });
  await expect
    .poll(() =>
      page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
    )
    .toBe(true);
});

test("server failure keeps form values for retry", async ({ page }) => {
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({
      json: {
        id: "sample-user",
        email: "sample@example.invalid",
        authenticated: true,
      },
    }),
  );
  await page.route("**/api/businesses", (r) =>
    r.fulfill({ status: 503, json: { error: { code: "request_failed" } } }),
  );
  await page.goto("/business/onboarding");
  await page.getByLabel("Business name").fill("Sample Cocoa");
  await page.getByLabel("Business sector").fill("Food");
  await page.getByLabel("Primary country or market").fill("Ghana");
  await page.getByLabel("Business goal").fill("Find buyers");
  await page
    .getByRole("button", { name: "Register business", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("unavailable");
  await expect(page.getByLabel("Business name")).toHaveValue("Sample Cocoa");
});

test("fictional onboarding and demo stay separate from business API", async ({
  page,
}) => {
  await page.route("**/api/auth/me", (r) =>
    r.fulfill({ status: 401, json: {} }),
  );
  const businessRequests: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/businesses")) businessRequests.push(r.url());
  });
  await page.goto("/onboarding");
  await page.getByLabel("Fictional business name").fill("Fictional Demo");
  await page
    .getByLabel("Your business goal")
    .fill("Explore sample connections");
  await page.getByRole("button", { name: "Enter local demo" }).click();
  await expect(page.locator(".demo-banner")).toContainText("LOCAL DEMO");
  expect(businessRequests).toEqual([]);
});
