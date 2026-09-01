import { expect, type Page, test } from "@playwright/test";

async function chooseUser(page: Page, name: string) {
  await page.goto("/login/");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible();
  const user = page.getByLabel("Usuario local");
  const option = user.locator("option", { hasText: name });
  await expect(option).toHaveCount(1, { timeout: 20_000 });
  await user.selectOption((await option.getAttribute("value")) as string);
  await page.getByRole("button", { name: "Continuar a la organización" }).click();
}

async function enterOrganization(page: Page, name: string) {
  await expect(page.getByRole("heading", { name: "Seleccionar organización" })).toBeVisible();
  const organization = page.getByLabel("Organización");
  const option = organization.locator("option", { hasText: name });
  await expect(option).toHaveCount(1, { timeout: 20_000 });
  await organization.selectOption((await option.getAttribute("value")) as string);
  await page.getByRole("button", { name: "Entrar al espacio de trabajo" }).click();
}

async function selectNamedVersion(page: Page, name: string) {
  const version = page.getByLabel("Versión");
  await expect(version).toBeVisible();
  const options = version.locator("option");
  await expect.poll(async () => options.count()).toBeGreaterThan(1);
  const labels = await options.allTextContents();
  const match = labels.find((label) => label.includes(name));
  expect(match, `expected a version labelled ${name}`).toBeTruthy();
  await version.selectOption({ label: match as string });
  await expect(page).toHaveURL(/version=/);
  await expect(version).toHaveValue(/.+/);
}

test("status screen loads after a local operator session", async ({ page }) => {
  await chooseUser(page, "Oli Operator");
  await page.goto("/estado/");
  await expect(page.getByRole("heading", { name: "Operación" })).toBeVisible({ timeout: 20_000 });
  await expect(
    page.getByText(/Sistema listo|Comprobando el estado|El sistema no está listo|No se pudo comprobar/),
  ).toBeVisible({ timeout: 20_000 });
});

test("zero-budget percent shows N/A on variances", async ({ page }) => {
  await chooseUser(page, "Ana Analyst");
  await enterOrganization(page, "Alpha");
  await page.getByRole("link", { name: "Variaciones" }).click();
  await expect(page.getByRole("heading", { name: "Variaciones" })).toBeVisible();
  const groupBy = page.getByLabel("Agrupar por");
  await expect(groupBy).toBeVisible();
  await groupBy.selectOption("account");
  await expect(page).toHaveURL(/group_by=account/);
  await selectNamedVersion(page, "Alpha");
  await expect(page.getByRole("button", { name: "Abrir detalle" }).first()).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("N/A").first()).toBeVisible();
});

test("department drill-down keeps filters in the breadcrumb", async ({ page }) => {
  await chooseUser(page, "Ana Analyst");
  await enterOrganization(page, "Alpha");
  await page.getByRole("link", { name: "Variaciones" }).click();
  await expect(page.getByRole("heading", { name: "Variaciones" })).toBeVisible();
  await selectNamedVersion(page, "Alpha");
  const detail = page.getByRole("button", { name: "Abrir detalle" }).first();
  await expect(detail).toBeVisible({ timeout: 20_000 });
  await detail.click();
  await expect(page).toHaveURL(/department=/);
  await expect(page.getByRole("navigation", { name: "breadcrumb" })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "breadcrumb" })).toContainText("Resumen");
});

test("switching organization drops Alpha context", async ({ page }) => {
  await chooseUser(page, "Pat Dual");
  await enterOrganization(page, "Alpha");
  await expect(page.getByRole("heading", { name: "Resumen" })).toBeVisible();
  await expect(page.getByText(/Periodo fiscal:.*MXN/)).toBeVisible({ timeout: 20_000 });
  const headerOrg = page.getByLabel("Organización");
  const beta = headerOrg.locator("option", { hasText: "Beta" });
  await expect(beta).toHaveCount(1);
  await headerOrg.selectOption((await beta.getAttribute("value")) as string);
  await expect(page.getByText(/Periodo fiscal:.*USD/)).toBeVisible({ timeout: 20_000 });
  await expect(page).not.toHaveURL(/department=/);
});
