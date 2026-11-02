import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
const routes = [
  "/",
  "/how-it-works",
  "/businesses",
  "/organizers",
  "/platform",
  "/signin",
  "/signup",
  "/onboarding",
  "/demo",
  "/demo/profile",
  "/demo/discover",
  "/demo/introductions",
  "/demo/opportunities",
  "/demo/events",
  "/demo/settings",
];
for (const viewport of [
  { width: 1440, height: 1000 },
  { width: 768, height: 1024 },
  { width: 390, height: 844 },
]) {
  test(`all routes render without overflow at ${viewport.width}px`, async ({
    page,
  }) => {
    await page.setViewportSize(viewport);
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    for (const route of routes) {
      await page.goto(route);
      await expect(page.locator("h1")).toBeVisible();
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
        )
        .toBe(true);
      await expect(page.locator("body")).not.toContainText("undefined");
    }
    expect(errors).toEqual([]);
  });
}
test("discovery, consent simulation, withdrawal and pipeline work locally", async ({
  page,
}) => {
  await page.goto("/demo/discover");
  await page.getByLabel("Search sample businesses").fill("akora");
  await expect(page.locator(".matches article")).toHaveCount(1);
  await page
    .getByRole("combobox", { name: "Market", exact: true })
    .selectOption("Nigeria");
  await expect(
    page.getByText("No sample matches fit these filters.", { exact: false }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Market", exact: true })
    .selectOption("Ghana");
  await page
    .getByRole("button", { name: "Save opportunity", exact: true })
    .click();
  await page.getByRole("button", { name: "Simulate introduction" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page
    .getByLabel("Your sample message")
    .fill("Sample distribution partnership inquiry.");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Save simulated request" }).click();
  await page.getByRole("link", { name: "Introductions", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Akora Distribution" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Withdraw request" }).click();
  await expect(page.getByText("Local simulation · withdrawn")).toBeVisible();
  await page.getByRole("link", { name: "Opportunities", exact: true }).click();
  await page
    .getByRole("combobox", { name: "Stage", exact: true })
    .selectOption("In conversation");
  await expect(
    page.getByRole("combobox", { name: "Stage", exact: true }),
  ).toHaveValue("In conversation");
  await page.getByRole("button", { name: "Remove", exact: true }).click();
  await expect(page.getByText("Room for your next opportunity.")).toBeVisible();
});
test("auth never creates a session, local onboarding persists sample profile", async ({
  page,
}) => {
  const requests: string[] = [];
  page.on("request", (r) => {
    if (r.method() === "POST") requests.push(r.url());
  });
  await page.goto("/signup");
  await page.getByRole("button", { name: /Continue with Google/ }).click();
  await expect(page.getByRole("status")).toContainText("not configured");
  await page.getByLabel("Your name").fill("Sample Person");
  await page.getByLabel("Email address").fill("sample@example.invalid");
  await page
    .getByLabel("Password (sample only)", { exact: true })
    .fill("dummy-preview-password");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Validate sign-up form" }).click();
  await expect(page.getByRole("status")).toContainText(
    "No account was created",
  );
  await page.goto("/onboarding");
  await page.getByLabel("Fictional business name").fill("Sample Cocoa Co.");
  await page
    .getByLabel("Your business goal")
    .fill("Explore fictional distribution");
  await page.getByRole("button", { name: "Enter local demo" }).click();
  await expect(page.locator(".sidebar")).toContainText("Sample Cocoa Co.");
  await page.reload();
  await expect(page.locator(".sidebar")).toContainText("Sample Cocoa Co.");
  expect(requests).toEqual([]);
});
test("keyboard navigation, modal escape, theme and reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page
    .getByRole("navigation", { name: "Main navigation" })
    .getByRole("link", { name: "Platform", exact: true })
    .click();
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "possibility",
  );
  await page.getByRole("button", { name: "Use dark theme" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.goto("/demo/discover");
  await page
    .getByRole("button", { name: "Simulate introduction" })
    .first()
    .click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".button").first()).toHaveCSS(
    "transition-duration",
    "0s",
  );
});
test("public and demo pages have no serious or critical automated accessibility violations", async ({
  page,
}) => {
  for (const theme of ["light", "dark"])
    for (const route of [
      "/",
      "/how-it-works",
      "/businesses",
      "/organizers",
      "/platform",
      "/signup",
      "/onboarding",
      "/demo/discover",
    ]) {
      await page.goto(route);
      if (
        theme === "dark" &&
        (await page.getByRole("button", { name: "Use dark theme" }).isVisible())
      )
        await page.getByRole("button", { name: "Use dark theme" }).click();
      const results = await new AxeBuilder({ page }).analyze();
      expect(
        results.violations
          .filter((v) => v.impact === "serious" || v.impact === "critical")
          .map((v) => ({ id: v.id, nodes: v.nodes.map((n) => n.target) })),
        `${theme} ${route}`,
      ).toEqual([]);
    }
});
test("capture review screenshots and verify all source images load", async ({
  page,
}) => {
  for (const width of [1440, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto("/");
    for (const img of await page.locator("img").all()) {
      await img.scrollIntoViewIfNeeded();
      await expect
        .poll(() =>
          img.evaluate(
            (el: HTMLImageElement) => el.complete && el.naturalWidth > 0,
          ),
        )
        .toBe(true);
    }
    await page.evaluate(async () => {
      await document.fonts.ready;
      window.scrollTo(0, 0);
    });
    await page.screenshot({
      path: `../work/home-${width}-light.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "Use dark theme" }).click();
    await page.screenshot({
      path: `../work/home-${width}-dark.png`,
      fullPage: true,
    });
    await page.getByRole("button", { name: "Use light theme" }).click();
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  for (const route of [
    "/how-it-works",
    "/businesses",
    "/organizers",
    "/platform",
    "/signup",
    "/demo/discover",
  ]) {
    await page.goto(route);
    for (const img of await page.locator("img").all()) {
      await img.scrollIntoViewIfNeeded();
      await expect
        .poll(() =>
          img.evaluate(
            (el: HTMLImageElement) => el.complete && el.naturalWidth > 0,
          ),
        )
        .toBe(true);
    }
    await page.evaluate(async () => {
      await document.fonts.ready;
      window.scrollTo(0, 0);
    });
    await page.screenshot({
      path: `../work/${route.slice(1).replaceAll("/", "-")}-desktop.png`,
      fullPage: true,
    });
  }
});
