import { expect, test } from "@playwright/test";

import { signInAs, waitForSelectedVersion } from "./helpers";

test.describe("mobile shell", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("opens navigation and reads the summary", async ({ page }) => {
    await signInAs(page, "Ana Analyst", "Alpha");
    await expect(page.getByRole("heading", { name: "Resumen" })).toBeVisible();
    await waitForSelectedVersion(page);
    await page.getByRole("button", { name: "Abrir navegación" }).click();
    await expect(page.getByRole("link", { name: "Variaciones", exact: true })).toBeVisible();
    await page.getByRole("link", { name: "Copiloto", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Copiloto" })).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: "Abrir navegación" }).click();
    await page.getByRole("link", { name: "Variaciones", exact: true }).click();
    await expect(page).toHaveURL(/\/variances/, { timeout: 20_000 });
    await expect(page.getByRole("heading", { name: "Variaciones", exact: true })).toBeVisible({
      timeout: 20_000,
    });
    await page.getByRole("button", { name: "Abrir filtros" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });
});

test.describe("tablet shell", () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test("keeps the summary readable and the import wizard usable", async ({ page }) => {
    await signInAs(page, "Ana Analyst", "Alpha");
    await expect(page.getByRole("heading", { name: "Resumen" })).toBeVisible();
    await waitForSelectedVersion(page);
    await page.goto("/imports/new/");
    await expect(page.getByRole("heading", { name: "Importar archivo" })).toBeVisible();
    await expect(
      page.getByText("El mapping masivo y la revisión de errores son más eficientes"),
    ).toBeVisible();
  });
});
