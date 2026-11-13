import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
});

for (const width of [1440, 768, 390]) {
  test(`global SurveyVista branding loads in both themes at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 950 });
    for (const route of ["/", "/platform", "/signin", "/demo", "/admin"]) {
      await page.goto(route);
      await expect(page.locator("footer .surveyvista-branding")).toHaveCount(1);
      await expect(page.locator("footer").getByText("Powered by SurveyVista (A Salesforce ISV Product)", { exact: true })).toBeVisible();
    }
    for (const theme of ["light", "dark"]) {
      if (theme === "dark") await page.getByRole("button", { name: "Use dark theme" }).click();
      const brand = page.locator("footer .surveyvista-branding");
      await brand.scrollIntoViewIfNeeded();
      await expect(brand).toHaveAttribute("href", "https://surveyvista.com/");
      const logo = brand.getByRole("img", { name: "SurveyVista", exact: true });
      await expect.poll(() => logo.evaluate(el => (el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
      const size = await logo.boundingBox();
      expect(size?.width).toBe(180);
      expect(size?.height).toBe(40);
      const layout = await brand.evaluate(el => {
        const logo = el.querySelector("img")!.getBoundingClientRect();
        const copy = el.querySelector("span")!.getBoundingClientRect();
        const tier = el.parentElement!.getBoundingClientRect();
        const box = el.getBoundingClientRect();
        return { stacked: copy.top >= logo.bottom, centered: Math.abs((box.left + box.right) / 2 - (tier.left + tier.right) / 2) < 1 };
      });
      expect(layout.centered).toBe(true);
      expect(layout.stacked).toBe(width <= 700);
      await expect(page.locator("footer").getByRole("link", { name: "Trust & architecture" })).toHaveAttribute("href", "/platform");
      await expect(page.locator("footer").getByRole("link", { name: "Explore local demo" })).toHaveAttribute("href", "/demo");
      await brand.focus();
      await expect(brand).toBeFocused();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const audit = await new AxeBuilder({ page }).include("footer").analyze();
      expect(audit.violations).toEqual([]);
      await page.locator("footer").screenshot({ path: `../work/surveyvista-footer-${width}-${theme}.png` });
    }
  });
}

test("public copy reflects connected integrations without obsolete sections", async ({
  page,
}) => {
  for (const path of [
    "/how-it-works",
    "/organizers",
    "/platform",
    "/signin",
    "/demo/settings",
    "/demo/events",
  ]) {
    await page.goto(path);
    await expect(page.locator("body")).not.toContainText(
      /EventSpark|Phase 1 preview|Salesforce: not connected|Email and Google entry methods are planned|Availability depends on future implementation|No event records or attendee outcomes shown here are live/,
    );
  }
  await page.goto("/platform");
  await expect(
    page.getByText(
      "Kobentra AI is designed around a secure Salesforce backend serving businesses in one centrally managed platform.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Secure Salesforce backend",
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "Membership authorization, scoped queries and consent enforcement.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText("Salesforce connected.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText("SurveyVista: connected.", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByText(
      /What can I use in this preview|Who can see my business information|Salesforce does not automatically isolate|Phase 1 makes no external/,
    ),
  ).toHaveCount(0);
  await page.goto("/organizers");
  await expect(page.locator(".usecases article")).toHaveCount(3);
  await expect(
    page.getByText("Honest integration status", { exact: true }),
  ).toHaveCount(0);
});

for (const width of [1440, 768, 390]) {
  test(`seamless responsive motion and accessible pause at ${width}px`, async ({
    page,
  }) => {
    await page.setViewportSize({ width, height: 950 });
    await page.goto("/");
    const track = page.locator(".ecosystem-track");
    await expect(page.locator("h1")).toBeVisible();
    expect(
      await page
        .locator("h1")
        .evaluate((el) => getComputedStyle(el).animationName),
    ).toBe("hero-copy-in");
    const geometry = await track.evaluate((el) => {
      const groups = Array.from(el.children).map(
        (group) => group.getBoundingClientRect().width,
      );
      return {
        groups,
        width: el.getBoundingClientRect().width,
        viewport: el.parentElement!.clientWidth,
      };
    });
    expect(Math.abs(geometry.groups[0] - geometry.groups[1])).toBeLessThan(1);
    expect(Math.abs(geometry.width / 2 - geometry.groups[0])).toBeLessThan(1);
    expect(geometry.groups[0]).toBeGreaterThanOrEqual(geometry.viewport - 1);
    const first = await track.evaluate((el) => getComputedStyle(el).transform);
    await expect
      .poll(() => track.evaluate((el) => getComputedStyle(el).transform))
      .not.toBe(first);
    // Scrub just before and at the loop boundary: one identical sequence replaces the other.
    const loop = await track.evaluate((el) => {
      const animation = el.getAnimations()[0];
      animation.pause();
      const duration = Number(animation.effect!.getTiming().duration);
      animation.currentTime = duration;
      const atLoop = getComputedStyle(el).transform;
      animation.currentTime = 0;
      const atStart = getComputedStyle(el).transform;
      animation.play();
      return { atLoop, atStart };
    });
    expect(loop.atLoop).toBe(loop.atStart);
    await page.locator(".ecosystem-marquee").hover();
    await expect
      .poll(() =>
        track.evaluate((el) => getComputedStyle(el).animationPlayState),
      )
      .toBe("paused");
    await page.locator("h1").hover();
    await page.locator(".ecosystem-marquee").focus();
    expect(
      await track.evaluate((el) => getComputedStyle(el).animationPlayState),
    ).toBe("paused");
    await page.getByRole("button", { name: "Pause ecosystem motion" }).click();
    await expect(
      page.getByRole("button", { name: "Resume ecosystem motion" }),
    ).toHaveAttribute("aria-pressed", "true");
    await page.getByRole("button", { name: "Resume ecosystem motion" }).click();
    const story = page.locator(".story").first();
    await story.scrollIntoViewIfNeeded();
    await expect(story).toHaveClass(/is-revealed/);
    await expect
      .poll(() =>
        story.evaluate(
          (el) =>
            el.getAnimations().filter((a) => a.playState === "running").length,
        ),
      )
      .toBe(0);
    await story.hover();
    await expect
      .poll(() => story.evaluate((el) => getComputedStyle(el).transform))
      .not.toBe("none");
    expect(await story.getAttribute("href")).toBe("/businesses");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: `../work/public-motion-${width}.png`,
      fullPage: true,
    });
  });
}

test("reduced motion shows all participants, keyboard navigation and accessible content", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await page.getByRole("button", { name: "Use dark theme" }).click();
  expect(
    await page
      .locator(".ecosystem-track")
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe("none");
  expect(
    await page
      .locator("h1")
      .evaluate((el) => getComputedStyle(el).animationName),
  ).toBe("none");
  for (const member of [
    "Buyers",
    "Suppliers",
    "Distributors",
    "Investors",
    "Partners",
  ]) {
    await expect(
      page
        .locator(".ecosystem-sequence")
        .first()
        .getByText(member, { exact: false }),
    ).toBeVisible();
  }
  await expect(page.locator(".ecosystem-sequence").nth(1)).toBeHidden();
  const contained = await page.locator(".ecosystem-marquee").evaluate(el => {
    const bounds = el.getBoundingClientRect();
    return Array.from(el.querySelectorAll(".ecosystem-sequence:first-child > span")).every(span => {
      const box = span.getBoundingClientRect();
      return box.left >= bounds.left && box.right <= bounds.right + 1 && box.bottom <= bounds.bottom + 1;
    });
  });
  expect(contained).toBe(true);
  await expect(
    page.getByRole("button", { name: "Pause ecosystem motion" }),
  ).toBeHidden();
  await page.locator(".ecosystem-marquee").focus();
  await expect(page.locator(".ecosystem-marquee")).toBeFocused();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(
    page.getByRole("link", { name: "How it works", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close navigation" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
  for (const image of await page.locator(".story img").all()) {
    await image.scrollIntoViewIfNeeded();
    await expect.poll(() => image.evaluate(el => (el as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
  }
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: "../work/public-motion-reduced-dark.png",
    fullPage: true,
  });
});

test("scroll content stays visible without IntersectionObserver", async ({
  page,
}) => {
  await page.addInitScript(() => {
    Object.defineProperty(window, "IntersectionObserver", {
      value: undefined,
      configurable: true,
    });
  });
  await page.goto("/");
  const card = page.locator(".story").first();
  await card.scrollIntoViewIfNeeded();
  await expect(card).toBeVisible();
  expect(await card.evaluate((el) => getComputedStyle(el).opacity)).toBe("1");
});
