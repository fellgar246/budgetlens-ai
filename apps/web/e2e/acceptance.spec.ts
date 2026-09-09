import { expect, test } from "@playwright/test";

import { chooseUser, openVariances, selectNamedVersion, signInAs } from "./helpers";

test("status screen loads after a local operator session", async ({ page }) => {
  await chooseUser(page, "Oli Operator");
  await page.goto("/estado/");
  await expect(page.getByRole("heading", { name: "Operación" })).toBeVisible({ timeout: 20_000 });
  await expect(
    page.getByText(
      /Sistema listo|Comprobando el estado|El sistema no está listo|No se pudo comprobar/,
    ),
  ).toBeVisible({ timeout: 20_000 });
});

test("zero-budget percent shows N/A on variances", async ({ page }) => {
  await signInAs(page, "Ana Analyst", "Alpha");
  await openVariances(page);
  const groupBy = page.getByLabel("Agrupar por");
  await expect(groupBy).toBeVisible();
  await groupBy.selectOption("account");
  await expect(page).toHaveURL(/group_by=account/, { timeout: 20_000 });
  await selectNamedVersion(page, "Alpha");
  await expect(page.getByRole("button", { name: "Abrir detalle" }).first()).toBeVisible({
    timeout: 20_000,
  });
  await expect(page.getByText("N/A").first()).toBeVisible();
});

test("department drill-down keeps filters in the breadcrumb", async ({ page }) => {
  await signInAs(page, "Ana Analyst", "Alpha");
  await openVariances(page);
  await selectNamedVersion(page, "Alpha");
  const detail = page.getByRole("button", { name: "Abrir detalle" }).first();
  await expect(detail).toBeVisible({ timeout: 20_000 });
  await detail.click();
  await expect(page).toHaveURL(/department=/, { timeout: 20_000 });
  const crumb = page.getByRole("navigation", { name: "breadcrumb" });
  await expect(crumb).toBeVisible();
  await expect(crumb).toContainText("Resumen");
  await crumb.getByRole("link", { name: "Todas las áreas" }).click();
  await expect(page).not.toHaveURL(/department=/);
});

test("switching organization drops Alpha context", async ({ page }) => {
  await signInAs(page, "Pat Dual", "Alpha");
  await expect(page.getByRole("heading", { name: "Resumen" })).toBeVisible();
  await expect(page.getByText(/Periodo fiscal:.*MXN/)).toBeVisible({ timeout: 20_000 });
  const headerOrg = page.getByLabel("Organización");
  const beta = headerOrg.locator("option", { hasText: "Beta" });
  await expect(beta).toHaveCount(1);
  await headerOrg.selectOption((await beta.getAttribute("value")) as string);
  await expect(page.getByText(/Periodo fiscal:.*USD/)).toBeVisible({ timeout: 20_000 });
  await expect(page).not.toHaveURL(/department=/);
  await expect(page.getByText(/Cambiaste a/)).toBeVisible();
});
