export const IMPORT_TEMPLATE_HEADERS = [
  "period",
  "account_code",
  "account_name",
  "account_type",
  "department_code",
  "department_name",
  "cost_center_code",
  "cost_center_name",
  "amount",
  "currency",
  "source_reference",
] as const;

const SAMPLE_ROW = [
  "2026-01-01",
  "6100",
  "Servicios externos",
  "expense",
  "OPS",
  "Operaciones",
  "CC-GEN",
  "General",
  "1000.0000",
  "MXN",
  "ERP-2026-01",
];

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
