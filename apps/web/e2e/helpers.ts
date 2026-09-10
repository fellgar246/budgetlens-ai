import { expect, type Page } from "@playwright/test";

export async function chooseUser(page: Page, name: string) {
  await page.goto("/login/");
  await expect(page.getByRole("heading", { name: "Iniciar sesión" })).toBeVisible({
    timeout: 20_000,
  });
  const user = page.getByLabel("Usuario local");
  const option = user.locator("option", { hasText: name });
  await expect(option).toHaveCount(1, { timeout: 20_000 });
  await user.selectOption((await option.getAttribute("value")) as string);
  await page.getByRole("button", { name: "Continuar a la organización" }).click();
}

export async function enterOrganization(page: Page, name: string) {
  await expect(page.getByRole("heading", { name: "Seleccionar organización" })).toBeVisible({
    timeout: 20_000,
  });
  const organization = page.getByLabel("Organización");
  const option = organization.locator("option", { hasText: name });
  await expect(option).toHaveCount(1, { timeout: 20_000 });
  await organization.selectOption((await option.getAttribute("value")) as string);
  await page.getByRole("button", { name: "Entrar al espacio de trabajo" }).click();
}

export async function signInAs(page: Page, userName: string, organizationName?: string) {
  await chooseUser(page, userName);
  if (organizationName) {
    await enterOrganization(page, organizationName);
    await expect(page.getByRole("heading", { name: "Resumen" })).toBeVisible({ timeout: 20_000 });
  }
}

export async function waitForSelectedVersion(page: Page) {
  const version = page.getByLabel("Versión");
  await expect(version).toBeVisible();
  await expect.poll(async () => version.inputValue(), { timeout: 20_000 }).not.toBe("");
  await expect(page).toHaveURL(/version=/, { timeout: 20_000 });
}

export async function openVariances(page: Page) {
  await waitForSelectedVersion(page);
  await page.getByRole("link", { name: "Variaciones" }).click();
  await expect(page).toHaveURL(/\/variances/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { name: "Variaciones", exact: true })).toBeVisible({
    timeout: 20_000,
  });
  await waitForSelectedVersion(page);
}

export async function waitForExportReady(page: Page) {
  await waitForSelectedVersion(page);
  await expect(page.getByRole("button", { name: "Exportar vista" })).toBeEnabled({
    timeout: 20_000,
  });
}
