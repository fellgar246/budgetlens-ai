# @budgetlens/api-client

Typed fetch helpers for the BudgetLens API.

`openapi.json` is generated from FastAPI. Refresh it with `make openapi` and commit the snapshot in the same change that alters the HTTP contract. Do not edit the snapshot by hand.

Each operation in the snapshot declares a stable `operationId`, `x-permission`, documented error envelope, examples for the public contract, and `X-Trace-Id`. The client is validated against that snapshot in the API unit suite. Keep path templates in `src/index.ts` aligned with the generated document.
