# Backlog 1.1

Unimplemented Should requirements are listed here as `deferred`. They must not disappear from the catalog. Could items stay behind any open Must or Should work.

Priority is the order a reviewer should discuss after the local portfolio demo. None of these are required to walk through [DEMO.md](DEMO.md).

## Deferred from the current baseline

| Order | ID | Source | Priority | Item |
|---|---|---|---|---|
| 1 | BL-1101 | FR-ORG-005 | Should | Archive an organization from the UI without physical delete |
| 2 | BL-1102 | FR-IMP-010 | Should | Explicitly replace an existing import data range |

## Candidates

| Order | ID | Source | Priority | Item | Why this order |
|---|---|---|---|---|---|
| 3 | BL-1104 | release-1.1 | Could | Multi-currency with an exchange-rate table | Most requested after a second legal entity |
| 4 | BL-1105 | release-1.1 | Could | 4-4-5 fiscal calendar | Needed before some retail actuals |
| 5 | BL-1103 | release-1.1 | Could | Statistical forecast with backtesting | Analytics after the calendar is honest |
| 6 | BL-1108 | release-1.1 | Could | Scheduled alerts | Notification after forecast or variance rules |
| 7 | BL-1107 | release-1.1 | Could | Executive PDF or PowerPoint export | Presentation after numbers are trusted |
| 8 | BL-1109 | release-1.1 | Could | Comments and approvals | Collaboration after a single-operator demo |
| 9 | BL-1106 | release-1.1 | Could | ERP integrations | Only after import replace (BL-1102) is real |
| 10 | BL-1110 | release-1.1 | Could | Managed queues or workers if volume requires them | Wait for an import-volume signal (ADR-001) |

See [TRACEABILITY.md](TRACEABILITY.md) and [RISKS.md](RISKS.md) (R-13).
