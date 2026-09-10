import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

import {
  openVariances,
  signInAs,
  waitForExportReady,
  waitForSelectedVersion,
} from "./helpers";

const sampleDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../../../sample-data",
);

test("local analyst can enter Alpha, open the summary, and reach variances", async ({ page }) => {
  await signInAs(page, "Ana Analyst", "Alpha");
  await expect(page.getByRole("heading", { name: "Resumen" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Variaciones" })).toBeVisible({ timeout: 20_000 });
  await waitForSelectedVersion(page);
  await expect(page.getByText(/Periodo fiscal/)).toContainText("MXN");
  await expect(page.getByText("Presupuesto", { exact: true }).first()).toBeVisible();
  await openVariances(page);
  await page.goto("/scenarios/");
  await expect(page.getByRole("heading", { name: "Escenarios", exact: true })).toBeVisible({
    timeout: 20_000,
  });
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
  await signInAs(page, "Ana Analyst", "Alpha");
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
  await expect(page.getByLabel("Periodo · Requerido")).toHaveValue("period");
  await page.getByRole("button", { name: "Vista previa" }).click();
  await expect(page.getByRole("button", { name: "Continuar" })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText("Hay filas que debes corregir antes de confirmar.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Continuar" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Descargar errores" })).toBeEnabled();
  await page.getByRole("button", { name: "Atrás" }).click();
  await expect(page.getByLabel("Periodo · Requerido")).toHaveValue("period");
  await page.getByRole("button", { name: "Cancelar importación" }).click();
});

test("valid budget import applies to a new draft version", async ({ page }) => {
  await signInAs(page, "Ana Analyst", "Alpha");
  const versionName = `E2E ${Date.now()}`;
  await page.goto("/settings/budget-versions/");
  await expect(page.getByRole("heading", { name: "Versiones de presupuesto" })).toBeVisible();
  await page.getByLabel("Nombre").fill(versionName);
  await page.getByLabel("Año fiscal").fill("2026");
  await page.getByRole("button", { name: "Crear versión" }).click();
  await expect(page.getByText(versionName)).toBeVisible({ timeout: 20_000 });

  await page.goto("/imports/new/");
  await page.getByLabel("Tipo de importación").selectOption("budget");
  const version = page.getByLabel("Versión");
  await expect.poll(async () => version.locator("option").count()).toBeGreaterThan(1);
  const labels = await version.locator("option").allTextContents();
  const match = labels.find((label) => label.includes(versionName));
  expect(match).toBeTruthy();
  await version.selectOption({ label: match as string });
  await page
    .locator('input[type="file"]')
    .first()
    .setInputFiles({
      name: "budget-valid.csv",
      mimeType: "text/csv",
      buffer: readFileSync(path.join(sampleDir, "budget-valid.csv")),
    });
  await expect(page.getByText(/Archivo seleccionado/)).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Vista previa" }).click();
  await expect(page.getByRole("button", { name: "Continuar" })).toBeEnabled({ timeout: 30_000 });
  await page.getByRole("button", { name: "Continuar" }).click();
  await page.getByRole("button", { name: "Confirmar importación" }).click();
  await expect(page.getByText("La importación se aplicó correctamente.")).toBeVisible({
    timeout: 30_000,
  });
});

test("login controls are labelled and the document language is Spanish", async ({ page }) => {
  await page.goto("/login/");
  await expect(page.locator("html")).toHaveAttribute("lang", "es");
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByLabel("Usuario local")).toBeVisible();
  await expect(page.getByRole("button", { name: "Continuar a la organización" })).toBeVisible();
});

test("filters survive refresh and browser back after drill-down", async ({ page }) => {
  await signInAs(page, "Ana Analyst", "Alpha");
  await waitForSelectedVersion(page);
  await expect(page.getByText("Presupuesto", { exact: true }).first()).toBeVisible({
    timeout: 20_000,
  });
  const summaryUrl = page.url();
  await page.reload();
  await expect(page).toHaveURL(summaryUrl);
  await expect(page.getByText("Presupuesto", { exact: true }).first()).toBeVisible({
    timeout: 20_000,
  });

  await openVariances(page);
  const beforeDrill = page.url();
  const detail = page.getByRole("button", { name: "Abrir detalle" }).first();
  await expect(detail).toBeVisible({ timeout: 20_000 });
  await detail.click();
  await expect(page).toHaveURL(/department=/, { timeout: 20_000 });
  await page.goBack();
  await expect(page).toHaveURL(beforeDrill, { timeout: 10_000 });
  await expect(page).not.toHaveURL(/department=/);
});

test("export dialog repeats the visible variance scope", async ({ page }) => {
  await signInAs(page, "Ana Analyst", "Alpha");
  await openVariances(page);
  await waitForExportReady(page);
  await page.getByLabel("Agrupar por").selectOption("account");
  await expect(page).toHaveURL(/group_by=account/, { timeout: 20_000 });
  await waitForExportReady(page);
  await page.getByRole("button", { name: "Exportar vista" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText("El CSV conservará los filtros y el desglose actuales.");
  await expect(dialog).toContainText("Cuenta");
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

test("scenario builder previews impact and saves without publishing the baseline", async ({
  page,
}) => {
  test.setTimeout(90_000);
  await signInAs(page, "Ana Analyst", "Alpha");
  await page.goto("/scenarios/new/");
  await expect(page.getByRole("heading", { name: "Escenarios", exact: true })).toBeVisible();
  const name = `Escenario E2E ${Date.now()}`;
  await page.getByLabel("Nombre del escenario").fill(name);
  const baseline = page.getByLabel("Línea base");
  await expect.poll(async () => baseline.locator("option").count()).toBeGreaterThan(1);
  const labels = await baseline.locator("option").allTextContents();
  const match = labels.find((label) => label.includes("Alpha") || label.includes("Budget"));
  expect(match).toBeTruthy();
  await baseline.selectOption({ label: match as string });
  await expect(page.getByText(/Impacto total/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("button", { name: "Guardar escenario" })).toBeEnabled({
    timeout: 20_000,
  });
  await page.getByRole("button", { name: "Guardar escenario" }).click();
  await expect(page).toHaveURL(/scenarios\/detail/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { name: /Comparación línea base/ })).toBeVisible();
  await page.goto("/scenarios/");
  await expect(page.getByRole("heading", { name: "Escenarios", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name })).toBeVisible({ timeout: 20_000 });
});

test("copilot answers Maintenance in January with matching evidence", async ({ page }) => {
  test.setTimeout(90_000);
  await signInAs(page, "Ana Analyst", "Alpha");
  await waitForSelectedVersion(page);
  await expect(page.getByRole("link", { name: "Preguntar al copiloto" })).toBeVisible();
  await page.getByRole("link", { name: "Preguntar al copiloto" }).click();
  await expect(page.getByRole("heading", { name: "Copiloto" })).toBeVisible({ timeout: 20_000 });
  await waitForSelectedVersion(page);
  await page.getByLabel("Preguntar").fill("¿Cuál fue la variación de Maintenance en enero?");
  await page.getByRole("button", { name: "Preguntar", exact: true }).click();
  await expect(page.getByText("Según el resumen", { exact: false })).toBeVisible({
    timeout: 30_000,
  });
  await expect(page.getByText(/Evidencia: ev_/)).toBeVisible();
  await expect(page.getByText("Resumen de variación")).toBeVisible();
});

test("keyboard opens a table drill-down control", async ({ page }) => {
  await signInAs(page, "Ana Analyst", "Alpha");
  await openVariances(page);
  const detail = page.getByRole("button", { name: "Abrir detalle" }).first();
  await expect(detail).toBeVisible({ timeout: 20_000 });
  await detail.focus();
  await expect(detail).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/department=/, { timeout: 20_000 });
});
