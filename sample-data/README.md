# Synthetic sample files

These workbooks and CSVs are invented for local tests and the demo. They are not a real company ledger. Do not add customer files here.

Alpha eval amounts match `apps/api` seed and the copilot evaluation dataset (FY2026, MXN, version name `Budget Final`). Beta seed uses exclusive amounts so a cross-tenant leak is visible in tests.

## Files

| File | Role |
|---|---|
| `budget-valid.csv` | Valid Alpha budget rows (periods 2026-01–2026-03) |
| `actuals-valid.csv` | Matching Alpha actuals |
| `budget-valid.xlsx` | Same valid budget as a workbook |
| `invalid-row.csv` | A row that must fail validation and block commit |
| `formula.xlsx` | Formula workbook that must be rejected and not applied |
| `unknown-dimension.csv` | Unknown catalog code |
| `duplicates.csv` | Duplicate keys |
| `locale-ambiguous.csv` | Ambiguous decimal/thousands separators |
| `leading-zero.csv` | Codes that must keep leading zeros |

## Reproduce the demo ledger

```text
make seed
```

Or import `budget-valid.csv` and `actuals-valid.csv` from the web **Importaciones** flow after signing in as Ana Analyst / Alpha.

Expected checkable facts after a valid Alpha import or seed:

- Maintenance January variance amount `30000.0000`, unfavorable
- Payroll January–February budget `400000.0000`, actual `403000.0000`
- Emergency March percent is unbounded (UI shows `N/A`)
- Unused March is no activity

Currency on these files is MXN. Beta is USD and is not in these CSVs.
