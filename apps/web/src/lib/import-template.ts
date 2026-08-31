export const IMPORT_TEMPLATE_HEADERS = [
  "period",
  "account_code",
  "department_code",
  "cost_center_code",
  "amount",
  "currency",
] as const;

const SAMPLE_ROW = ["2026-01-01", "6100", "OPS", "CC-GEN", "1000.0000", "MXN"];

export function importTemplateCsv(): string {
  return `${IMPORT_TEMPLATE_HEADERS.join(",")}\n${SAMPLE_ROW.join(",")}\n`;
}

export function downloadImportTemplate(): void {
  const blob = new Blob([importTemplateCsv()], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "budgetlens-plantilla.csv";
  link.click();
  URL.revokeObjectURL(url);
}
