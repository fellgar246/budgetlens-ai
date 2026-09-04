export const CANONICAL_IMPORT_FIELDS = [
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

export const REQUIRED_IMPORT_FIELDS = [
  "period",
  "account_code",
  "department_code",
  "amount",
  "currency",
] as const;

export function sampleValuesForHeader(
  rows: Array<Record<string, string>>,
  header: string,
  limit = 2,
): string {
  const values: string[] = [];
  for (const row of rows) {
    const value = (row[header] ?? "").trim();
    if (value && !values.includes(value)) {
      values.push(value);
      if (values.length >= limit) {
        break;
      }
    }
  }
  return values.join(", ");
}

export function requiredMappingComplete(
  mapping: Record<string, string>,
  required: readonly string[] = REQUIRED_IMPORT_FIELDS,
): boolean {
  return required.every((field) => Boolean(mapping[field]?.trim()));
}
