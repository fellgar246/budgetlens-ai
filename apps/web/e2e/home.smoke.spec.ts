import { expect, test } from "@playwright/test";

test("home page renders the product shell", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("body")).toContainText("BudgetLens");
});
