# Traceability

This catalog is the product record of requirements, acceptance, plans, and external gates. A requirement that is not implemented is marked `deferred` and added to `docs/BACKLOG.md`. Identifiers are stable and are not reused.

## Functional matrix

| Requirements | Primary area | Plans | Acceptance |
|---|---|---|---|
| FR-ORG-001–005 | Product/API/Security | 01, 06 | AC-011, AC-013, AC-015 |
| FR-DIM-001–003 | Domain/API | 01, 04 | Domain/API tests and settings journeys |
| FR-BUD-001–004 | Business rules/API | 01, 04 | AC-002, AC-005–010 (indirect) and version state tests |
| FR-IMP-001–010 | Import/export contract | 02, 04 | AC-002–004, AC-014 |
| FR-ANA-001–009 | Business rules/API/UX | 03, 04 | AC-005–010 |
| FR-AI-001–009 | AI architecture/dataset | 05, 06 | AC-017–022 |
| FR-AUD-001–003 | Observability/audit | 01, 02, 05, 07 | AC-011, AC-016, AC-023–025 |
| FR-OPS-001–004 | Observability/infrastructure | 00, 07–10 | AC-023–026 |
| FR-UI-001–005 | UX/UI + UI guidelines | 04–06 | Journeys, keyboard use, AC-013 |

### Functional status

| ID | Priority | Status |
|---|---|---|
| FR-ORG-001 | Must | Implemented |
| FR-ORG-002 | Must | Implemented |
| FR-ORG-003 | Must | Implemented |
| FR-ORG-004 | Must | Implemented |
| FR-ORG-005 | Should | Deferred — BL-1101 |
| FR-DIM-001 | Must | Implemented |
| FR-DIM-002 | Must | Implemented |
| FR-DIM-003 | Must | Implemented |
| FR-BUD-001 | Must | Implemented |
| FR-BUD-002 | Must | Implemented |
| FR-BUD-003 | Must | Implemented |
| FR-BUD-004 | Must | Implemented |
| FR-IMP-001 | Must | Implemented |
| FR-IMP-002 | Must | Implemented |
| FR-IMP-003 | Must | Implemented |
| FR-IMP-004 | Must | Implemented |
| FR-IMP-005 | Must | Implemented |
| FR-IMP-006 | Must | Implemented |
| FR-IMP-007 | Must | Implemented |
| FR-IMP-008 | Must | Implemented |
| FR-IMP-009 | Should | Implemented |
| FR-IMP-010 | Should | Deferred — BL-1102 |
| FR-ANA-001 | Must | Implemented |
| FR-ANA-002 | Must | Implemented |
| FR-ANA-003 | Must | Implemented |
| FR-ANA-004 | Must | Implemented |
| FR-ANA-005 | Must | Implemented |
| FR-ANA-006 | Must | Implemented |
| FR-ANA-007 | Must | Implemented |
| FR-ANA-008 | Should | Implemented |
| FR-ANA-009 | Should | Implemented |
| FR-AI-001 | Must | Implemented |
| FR-AI-002 | Must | Implemented |
| FR-AI-003 | Must | Implemented |
| FR-AI-004 | Must | Implemented |
| FR-AI-005 | Must | Implemented |
| FR-AI-006 | Must | Implemented |
| FR-AI-007 | Must | Implemented |
| FR-AI-008 | Must | Implemented |
| FR-AI-009 | Must | Partial — stub eval exists; live Bedrock remains gated |
| FR-AUD-001 | Must | Implemented |
| FR-AUD-002 | Must | Implemented |
| FR-AUD-003 | Should | Implemented |
| FR-OPS-001 | Must | Implemented |
| FR-OPS-002 | Must | Implemented |
| FR-OPS-003 | Must | Implemented |
| FR-OPS-004 | Must | Implemented |
| FR-UI-001 | Must | Implemented |
| FR-UI-002 | Must | Implemented |
| FR-UI-003 | Must | Implemented |
| FR-UI-004 | Should | Implemented |
| FR-UI-005 | Must | Implemented |

## Non-functional matrix

| Requirements | Plans | Evidence |
|---|---|---|
| NFR-PERF-001–005 | 02, 03, 04, 05, 07 | Import/API benchmark scripts, Lighthouse pending, AI telemetry, pagination tests |
| NFR-REL-001–005 | 02, 07, 09, 10 | Atomic import tests, health, rollback/restore runbook |
| NFR-SEC-001–007 | 02, 05–10 | Upload/security tests, tenant matrix, scans, AWS review pending |
| NFR-PRI-001–005 | 02, 05–10 | Log tests, retention, synthetic seed, presigned export flow |
| NFR-UX-001–004 | 04, 07 | Automated display tests, keyboard/focus styles, format components |
| NFR-MNT-001–006 | 00–09 | Coverage gates, types, migrations, OpenAPI, [decisions](DECISIONS.md) |
| NFR-OBS-001–004 | 00, 05, 07, 08, 10 | Trace/log/metrics/alarm tests and AWS smoke still pending |

Individual IDs: NFR-PERF-001, NFR-PERF-002, NFR-PERF-003, NFR-PERF-004, NFR-PERF-005, NFR-REL-001, NFR-REL-002, NFR-REL-003, NFR-REL-004, NFR-REL-005, NFR-SEC-001, NFR-SEC-002, NFR-SEC-003, NFR-SEC-004, NFR-SEC-005, NFR-SEC-006, NFR-SEC-007, NFR-PRI-001, NFR-PRI-002, NFR-PRI-003, NFR-PRI-004, NFR-PRI-005, NFR-UX-001, NFR-UX-002, NFR-UX-003, NFR-UX-004, NFR-MNT-001, NFR-MNT-002, NFR-MNT-003, NFR-MNT-004, NFR-MNT-005, NFR-MNT-006, NFR-OBS-001, NFR-OBS-002, NFR-OBS-003, NFR-OBS-004.

## Plans

Each plan declares the requirements and acceptance it owns. The machine-readable copy lives with the unit suite and is checked on every `make test`.

| Plan | Name | Status | Requirements | Acceptance |
|---|---|---|---|---|
| Plan 00 | Bootstrap | Complete | FR-OPS-001, FR-OPS-002, NFR-MNT-002, NFR-OBS-001 | AC-001, AC-023, AC-024 |
| Plan 01 | Domain foundation | Complete | FR-ORG-001–005, FR-DIM-001–003, FR-BUD-001–004, FR-AUD-001, NFR-MNT-001, NFR-MNT-003 | AC-006, AC-007, AC-015 |
| Plan 02 | Import pipeline | Implemented | FR-IMP-001–010, FR-AUD-001, NFR-PERF-003, NFR-REL-003, NFR-SEC-007, NFR-PRI-001 | AC-002, AC-003, AC-004, AC-014 |
| Plan 03 | Analytics | Implemented | FR-ANA-001–009, NFR-PERF-001 | AC-005–010 |
| Plan 04 | Frontend | Implemented | FR-UI-001–005, FR-ANA-003, FR-ANA-006, NFR-UX-001–004, NFR-PERF-002 | AC-002, AC-005, AC-008–010, AC-013 |
| Plan 05 | AI copilot | Implemented | FR-AI-001–009, FR-AUD-002, NFR-PERF-004, NFR-SEC-004, NFR-PRI-002, NFR-PRI-004, NFR-OBS-002 | AC-017–022 |
| Plan 06 | Auth and tenancy | Implemented | FR-ORG-002–004, NFR-SEC-003, NFR-SEC-004, NFR-PRI-001 | AC-011–016 |
| Plan 07 | Hardening | Implemented | FR-AUD-001, FR-AUD-003, FR-OPS-001–004, NFR-PERF-001/003/005, NFR-REL-003–005, NFR-SEC-005/006, NFR-PRI-003, NFR-PRI-005, NFR-MNT-005, NFR-OBS-001–004 | AC-016, AC-023–025 |
| Plan 08 | Terraform | Pending | NFR-SEC-001, NFR-SEC-002, NFR-REL-001, NFR-MNT-006, NFR-OBS-003 | AC-025 |
| Plan 09 | CI/CD | Pending | NFR-SEC-002, NFR-SEC-005, NFR-REL-005, NFR-MNT-004, FR-OPS-004 | AC-001, AC-025 |
| Plan 10 | AWS deployment | Blocked | NFR-REL-001, NFR-REL-002, NFR-SEC-001, FR-OPS-004, NFR-OBS-003 | AC-026 |
| Plan 11 | Portfolio release | Pending | FR-OPS-004, NFR-PRI-001 | AC-001 |

## Acceptance evidence

| ID | Kind | Evidence |
|---|---|---|
| AC-001 | Suite + runbook | `README.md`, `scripts/bootstrap.sh`, web health card test |
| AC-002 | Suite | Valid CSV/XLSX import integration test |
| AC-003 | Suite | Invalid row blocks commit |
| AC-004 | Suite | Idempotent commit retry |
| AC-005 | Suite | Zero-budget variance + `N/A` display |
| AC-006 | Suite | Expense over budget is unfavorable |
| AC-007 | Suite | Revenue over budget is favorable |
| AC-008 | Suite | Analytics totals and drill-down filters |
| AC-009 | Suite | Authorized, expiring export download |
| AC-010 | Suite | Scenario preview does not mutate entries |
| AC-011 | Suite | Cross-tenant read is 403/404 |
| AC-012 | Suite | Cross-tenant mutation is denied |
| AC-013 | Suite | Organization switch does not leak the previous tenant |
| AC-014 | Suite | Formula XLSX rejected |
| AC-015 | Suite | `AUTH_MODE=dev` fails closed outside local/test |
| AC-016 | Suite | Log sanitization |
| AC-017 | Suite | Grounded copilot + stub eval |
| AC-018 | Suite | No evidence, no invented cause |
| AC-019 | Suite | Mutation request refused |
| AC-020 | Suite | Safety eval treats injection as a label |
| AC-021 | Suite | Tool args cannot retarget another tenant |
| AC-022 | Suite | Tool-loop limit |
| AC-023 | Suite | Live/ready health |
| AC-024 | Suite | Empty and N-1 migrations |
| AC-025 | Runbook | [Images and rollback](OPERATIONS.md#images-and-rollback) |
| AC-026 | Runbook | [Restore](OPERATIONS.md#restore) |

AC-001 through AC-025 are required for release 1.0. AC-026 is required before calling the product production-ready.

## External gates

| Gate | Plans | Owner | Moment | Local simulation | Blocks |
|---|---|---|---|---|---|
| M-00 | Plan 01 | Domain owner | Before or during plan 01 | Yes, defaults | No if defaults are accepted |
| M-01 | Plan 08, Plan 10 | Security owner | Before a real Terraform plan | No | AWS |
| M-02 | Plan 05, 08–10 | Operator | Before remote bootstrap | Fake config | AWS |
| M-03 | Plan 08–10 | Operator | Before apply | Terraform code | AWS |
| M-04 | Plan 05, Plan 10 | AI owner | Live eval and AWS AI | Stub/contract mock | AWS AI |
| M-05 | Plan 09–10 | Engineering | Real pipeline enablement | Workflow lint | Real pipeline |
| M-06 | Plan 10–11 | Operator | Before a final production URL | Managed domain | Production URL |
| M-07 | Plan 06, Plan 10 | Security owner | Before third-party users | Test issuer/JWKS | Third-party users |
| M-08 | Plan 05, Plan 10 | Product/Security | Before real data | Local synthetic policy | Real data |
| M-09 | Plan 10 | Operator | Immediately before apply | No | AWS apply |
| M-10 | Plan 11 | Owner | Future production cutover | No | Production |

## Baseline coverage

The baseline is traceable when:

- every FR/NFR appears in a row above;
- every plan declares its requirements and acceptance;
- every AC has a suite or a runbook step;
- every external gate has an owner and a moment;
- every high-impact risk in [RISKS.md](RISKS.md) has a mitigation and a signal.

`make test` runs `apps/api/tests/unit/test_traceability.py`, which fails if any of those rules break.
