# Risk register

Scale for likelihood and impact: `low`, `medium`, `high`. The owner is a role, not necessarily a different person.

## Treatment

- A high-impact risk without a verifiable mitigation blocks the named release (`aws` and/or `prod`). Local development is not blocked by unverified cloud risks.
- If likelihood or impact changes, update the row and record the date in the plan close-out.
- A realized risk becomes an incident or issue and must add a regression test.
- Accepting a security, data, or external-cost risk requires an explicit human decision (`accepted_by` and `accepted_on`). An agent must not accept those risks by default.

## Register

| ID | Risk | P | I | Mitigation / gate | Owner | Trigger | Mitigation |
|---|---|---|---|---|---|---|---|
| R-01 | Incorrect calculation or rounding | M | H | Decimal, pure rules, AC-005–010 | Domain owner | Difference against fixture or control total | Verified |
| R-02 | Cross-tenant leak | M | H | Tenant context, isolation matrix, scoped tools | Security owner | IDOR test or audit anomaly | Verified |
| R-03 | Malicious or exhausting upload | M | H | Allowlist, limits, no formulas/macros, timeout | Engineering | Parser crash or memory spike | Verified |
| R-04 | Invented AI figures | H | H | Tools, grounding, evidence, eval gate | AI/Domain | Figure not in tool output or safety fail | Verified |
| R-05 | Prompt injection from data | M | H | Delimited data, closed tools, safety cases | Security owner | Tool or tenant changes because of a label | Verified |
| R-06 | Unexpected AWS cost | M | H | Budgets, tags, small dev, teardown, measurement | Operator | Forecast or actual exceeds the threshold | Unverified — blocks AWS/prod |
| R-07 | NAT/RDS dominate demo cost | H | M | Measure, stop or destroy, record an alternative | Operator | Baseline week exceeds the cost objective | Unverified |
| R-08 | Migration prevents rollback | M | H | Expand/contract, one-off jobs, N-1 tests | Engineering | Deploy requires a schema downgrade | Verified |
| R-09 | Bedrock or model unavailable | M | M | Model config, stub, region gate, adapter | AI owner | M-04 not completed | Verified (local stub) |
| R-10 | API change breaks the frontend | M | M | OpenAPI snapshot and client drift gate | Engineering | CI contract failure | Verified |
| R-11 | Performance degrades at 250k rows | M | M | SQL aggregates, indexes, EXPLAIN in integration, local load script | Engineering | p95 misses the read threshold | Partial — CI proves index use; 250k p95 stays a local measurement |
| R-12 | Secret in a log, state file, or build | M | H | Secret tests/scans, OIDC, sensitive outputs | Security owner | Scanner or log assertion | Verified |
| R-13 | Excess design delays the MVP | M | M | Must/Should/Could, one plan at a time | Product | Could work starts before Must work | Verified |
| R-14 | Dependency or provider change | M | M | Lockfiles, adapters, decision record, eval on upgrade | Engineering | Renovate or provider update | Verified |
| R-15 | Backups are not restorable | L | H | Isolated restore (AC-026) | Operator | Restore test fails | Unverified — blocks AWS/prod |
| R-16 | Dev auth reaches the cloud | L | H | Startup invariant AC-015 | Security owner | Forbidden config combination detected | Verified |
| R-17 | Personal or real information in the demo | M | H | Synthetic-only seed, repository and log review | Product/Security | Scan or review finds real data | Verified |
| R-18 | Single-person project without operational capacity | M | M | Runbooks, simple architecture, alerts | Owner | Incident the runbook cannot resolve | Partial |

No risk in this register is marked realized. If one is, add an incident reference and a regression path before closing the change.
