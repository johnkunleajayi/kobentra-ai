import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
test("modal traps keyboard focus, restores trigger and exposes accessible controls", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/demo/discover");
  const trigger = page
    .getByRole("button", { name: "Simulate introduction" })
    .first();
  await trigger.click();
  const close = page.getByRole("button", { name: "Close introduction" });
  await expect(close).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await expect(
    page.getByRole("button", { name: "Save simulated request" }),
  ).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(close).toBeFocused();
  const result = await new AxeBuilder({ page }).analyze();
  expect(
    result.violations
      .filter((v) => v.impact === "serious" || v.impact === "critical")
      .map((v) => v.id),
  ).toEqual([]);
  await page.screenshot({ path: "../work/introduction-modal-mobile.png" });
  await page.keyboard.press("Escape");
  await expect(trigger).toBeFocused();
});
