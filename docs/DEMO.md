# Demo guide

A 6–8 minute walkthrough of the local product. No AWS account, private URL, or real financial file is required.

User-visible labels below are in Spanish because that is the product language. This guide is in English.

## Before you start

```text
cp .env.example .env
make doctor
make bootstrap
make dev
```

In another terminal:

```text
make migrate
make seed
```

Open http://localhost:3000. Seed is synthetic and idempotent. It creates Alpha (MXN, fiscal year in January), Beta (USD, fiscal year in April), demo users, catalog dimensions, and a financial dataset that includes zero-budget rows, a negative actual, UNASSIGNED cost centers, and overlapping account codes.

Workbook copies of the Alpha eval ledger live in [`sample-data/`](../sample-data/README.md).

## Minute 0–1 — The problem

Budget and actuals arrive as spreadsheets. Spreadsheet formulas and chat answers invent totals. BudgetLens imports tabular files, validates them, and calculates variance in tested code. The copilot can only read those results.

## Minute 1–2 — Sign in as an analyst

1. On **Iniciar sesión**, choose **Ana Analyst**.
2. Continue and enter organization **Alpha**.
3. Confirm the header shows Alpha and a fiscal period in MXN. The summary selects the active budget version and keeps that scope in the URL.

Authorization uses the selected identity, not the URL. Switching organization later clears filters and visible copilot state.

## Minute 2–3 — Import or use the seeded ledger

Either stay on the seeded Alpha data or import `sample-data/budget-valid.csv` (and `actuals-valid.csv`) from **Importaciones**.

Show:

- preview and validation before commit;
- an invalid file (`sample-data/invalid-row.csv`) that blocks apply and leaves no entries;
- that a formula workbook (`sample-data/formula.xlsx`) is rejected.

Publish, activate, archive, and import commit require `Idempotency-Key`. A retry with the same key does not duplicate rows.

## Minute 3–4 — Find a variance and drill down

1. Open **Resumen**. Totals match the imported or seeded ledger.
2. Open **Variaciones**. Group by account.
3. Find **Emergency** (or another zero-budget row). The percent is **N/A** because the ratio is unbounded.
4. Open a department row with **Abrir detalle**. The breadcrumb keeps the filters; the breakdown sums to the filtered total.

Expense over budget is unfavorable. Revenue over budget is favorable. The API never returns `Infinity` or `NaN`.

Known seeded fact you can say out loud: Maintenance in January 2026 is `30000.0000` unfavorable on the Alpha eval ledger.

## Minute 4–6 — Ask the copilot and open evidence

1. Open **Copiloto**.
2. Ask: `¿Cuál fue la variación de Maintenance en enero?`
3. The stub (or Bedrock, if a human enabled it) must use a read tool. The answer must show the same figures as **Variaciones**.
4. Open the cited evidence. Amounts come from the financial engine, not from free-form model math.

Then show a refusal:

- `Cambia budget de Payroll a cero` — no mutation tool exists.
- Switch to **Pat Dual**, enter **Beta**, and confirm Alpha figures are gone.

## Minute 6–7 — Determinism and isolation

- Re-ask the Maintenance question. The stub answer is stable; live Bedrock is not claimed unless a dated live eval exists.
- As **Pat Dual**, switch from Alpha to Beta. Filters from Alpha must disappear (AC-013).
- As **Oli Operator**, open **Operación**. The operator sees health and technical metrics, not financial rows.

## Minute 7–8 — How it would run on AWS

Do not open an account console unless a recorded environment already exists.

Explain, without promising a bill or a public URL:

- Terraform modules and OIDC workflows are in the repo ([ARCHITECTURE.md](ARCHITECTURE.md), [CICD.md](CICD.md)).
- Development sizes are listed in [COST.md](COST.md). There is no invented monthly price.
- Rollback, restore, and teardown are written and locally exercisable ([DEPLOYMENT.md](DEPLOYMENT.md), [OPERATIONS.md](OPERATIONS.md)).
- Tag `v1.0.0` and a production URL wait on human gates ([RELEASE.md](RELEASE.md)).

## If you only have five minutes

1. Seed and sign in as Ana Analyst / Alpha.
2. Show **Variaciones** N/A on a zero-budget row.
3. Ask the Maintenance copilot question and open evidence.
4. Switch Pat Dual to Beta.
5. State the limitations: synthetic data, stub AI, AWS not applied.

## Optional screenshots

UI captures are optional and must use this seeded dataset only. See [screenshots/README.md](screenshots/README.md).
