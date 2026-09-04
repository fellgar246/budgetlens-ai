import { expect, type Page, test } from "@playwright/test";

async function signInAsAlphaAnalyst(page: Page) {
  await page.goto("/login/");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  const user = page.getByLabel("Usuario local");
  const analyst = user.locator("option", { hasText: "Ana Analyst" });
  await expect(analyst).toHaveCount(1, { timeout: 20_000 });
  await user.selectOption((await analyst.getAttribute("value")) as string);
  await page.getByRole("button", { name: "Continuar a la organización" }).click();
  await expect(page.getByRole("heading", { name: "Seleccionar organización" })).toBeVisible();
  const organization = page.getByLabel("Organización");
  const alpha = organization.locator("option", { hasText: "Alpha" });
  await expect(alpha).toHaveCount(1, { timeout: 20_000 });
  await organization.selectOption((await alpha.getAttribute("value")) as string);
  await page.getByRole("button", { name: "Entrar al espacio de trabajo" }).click();
}

test("local analyst can enter Alpha, open the summary, and reach variances", async ({ page }) => {
  await signInAsAlphaAnalyst(page);
  await expect(page.getByRole("heading", { name: "Resumen" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Variaciones" })).toBeVisible({ timeout: 20_000 });
  const version = page.getByLabel("Versión");
  await expect(version).toBeVisible();
  const options = version.locator("option");
  await expect.poll(async () => options.count()).toBeGreaterThan(1);
  const labels = await options.allTextContents();
  const match = labels.find((label) => label.includes("Alpha"));
  if (match) {
    await version.selectOption({ label: match });
    await expect(page.getByText(/Periodo fiscal/)).toContainText("MXN");
    await expect(page.getByText("Presupuesto")).toBeVisible();
  }
  await page.getByRole("link", { name: "Variaciones" }).click();
  await expect(page.getByRole("heading", { name: "Variaciones" })).toBeVisible();
  await page.getByRole("link", { name: "Escenarios" }).click();
  await expect(page.getByRole("heading", { name: "Escenarios" })).toBeVisible();
});

test("keyboard reaches skip link and main content", async ({ page }) => {
  await page.goto("/login/");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Saltar al contenido" });
  await expect(skip).toBeFocused();
  await skip.press("Enter");
  await expect(page.locator("#contenido")).toBeFocused();
});

test("import wizard keeps mapping, blocks commit on errors, and offers a download", async ({
  page,
}) => {
  await signInAsAlphaAnalyst(page);
  await page.goto("/imports/new/");
  await expect(page.getByRole("heading", { name: "Importar archivo" })).toBeVisible();
  await page.getByLabel("Tipo de importación").selectOption("actual");
  const csv = [
    "period,account_code,department_code,cost_center_code,amount,currency",
    "2026-01,6100,OPS,CC-GEN,not-a-number,MXN",
  ].join("\n");
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles({
      name: "invalid-actuals.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(csv),
    });
  await expect(page.getByText(/Archivo seleccionado/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByLabel("period · Requerido")).toHaveValue("period");
  await page.getByRole("button", { name: "Vista previa" }).click();
  await expect(page.getByRole("button", { name: "Continuar" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Hay filas que debes corregir antes de confirmar.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Descargar errores" })).toBeEnabled();
  await page.getByRole("button", { name: "Atrás" }).click();
  await expect(page.getByLabel("period · Requerido")).toHaveValue("period");
  await page.getByRole("button", { name: "Cancelar importación" }).click();
});

test("login controls are labelled and the document language is Spanish", async ({ page }) => {
  await page.goto("/login/");
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByLabel("Usuario local")).toBeVisible();
  await expect(page.getByRole("button", { name: "Continuar a la organización" })).toBeVisible();
});
