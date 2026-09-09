# Architecture decisions

Accepted decisions that affect the shape of the product. Do not rewrite an accepted entry. Add a new numbered record and mark the previous one `superseded` when a change is required. Irreversible or costly changes require a new row (NFR-MNT-006).

Statuses: `proposed`, `accepted`, `superseded`, `rejected`.

A `proposed` record is not an accepted decision. Local synthetic defaults may continue; production behavior stays gated until a human accepts the record.

## How to add a decision

Add an ADR with number, date, status, context, decision, positive and negative consequences, discarded alternatives, and affected plans or requirements.

## Index

| ID | Status | Decision |
|---|---|---|
| ADR-001 | accepted | Modular monolith: one API deployable; workers reuse the same codebase |
| ADR-002 | accepted | Deterministic financial calculations stay outside the LLM; the model only calls tools |
| ADR-003 | accepted | PostgreSQL `numeric(19,4)`, Python `Decimal`, JSON amounts as strings |
| ADR-004 | accepted | Next.js static export behind CloudFront; no required SSR |
| ADR-005 | accepted | FastAPI on ECS Fargate behind an ALB |
| ADR-006 | accepted | Application authorization plus PostgreSQL row-level security |
| ADR-007 | accepted | Ports for object storage, identity, and AI; local adapters for development |
| ADR-008 | accepted | Terraform state in versioned/encrypted S3 with native lockfile; no new DynamoDB lock table |
| ADR-009 | accepted | CI assumes AWS through GitHub OIDC; no permanent access keys |
| ADR-010 | accepted | One functional currency and monthly periods in 1.0 |
| ADR-011 | accepted | Import execution behind an interchangeable `ImportExecutor` |
| ADR-012 | proposed | Conversation persistence policy (full encrypted text vs redacted). Local synthetic content is allowed; production waits for a human decision |
| ADR-013 | accepted | In-process portable metrics and W3C `traceparent`; no vendor telemetry SDK in the API process |

## ADR-001 — Modular monolith

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** The product needs a single operable backend for API, imports, and maintenance jobs without a microservice mesh.
- **Decision:** Ship one FastAPI deployable. Workers reuse the same package and image; the entrypoint can run the API or `python -m budgetlens`.
- **Positive consequences:** One build, one migration path, and shared domain rules for API and jobs.
- **Negative consequences:** Modules communicate in-process. Extracting a network service later needs evidence and a new ADR.
- **Alternatives:** Separate import and API services from day one. Rejected: operational cost without a volume signal.
- **Affected plans / requirements:** Plans 00–07, 10; NFR-MNT-005; BL-1110.

## ADR-002 — Deterministic calculations stay outside the LLM

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Language models invent figures and cannot be the source of budget versus actuals.
- **Decision:** The model only selects registered tools. Amounts, aggregations, variances, and scenario previews are computed in tested domain or SQL code.
- **Positive consequences:** Answers are auditable and reproducible; evals can check grounding.
- **Negative consequences:** Tool contracts and evidence hashes require more work than free-form SQL.
- **Alternatives:** Let the model write SQL or compute amounts. Rejected: not auditable.
- **Affected plans / requirements:** Plan 05; FR-AI-001–009; AC-017–022.

## ADR-003 — Decimal money and JSON strings

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Binary floating point cannot represent money exactly.
- **Decision:** Store amounts as PostgreSQL `numeric(19,4)`, use Python `Decimal` / `MoneyAmount`, and serialize JSON amounts as decimal strings. The web formats those strings and does not use `number` arithmetic for canonical values.
- **Positive consequences:** Rounding is explicit and fixtures stay stable.
- **Negative consequences:** Clients must parse decimal strings instead of native JSON numbers.
- **Alternatives:** JSON numbers or integer cents. Rejected: precision loss or hidden scale.
- **Affected plans / requirements:** Plans 01–04; NFR-UX-004; R-01.

## ADR-004 — Next.js static export on AWS

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** The web app has no required server-side rendering. Auth and data already live in the browser and API.
- **Decision:** Use the App Router with `output: "export"` and deploy static assets to a private S3 bucket behind CloudFront.
- **Positive consequences:** No frontend container, simpler cache, and a cheap static origin.
- **Negative consequences:** Session and data fetching stay on the client. Introducing SSR requires a new ADR and a deployment review.
- **Alternatives:** A Next.js Node server on ECS. Rejected: extra runtime without a product need.
- **Affected plans / requirements:** Plans 04, 08, 10; FR-UI-001–005.

## ADR-005 — FastAPI on ECS Fargate

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Imports process files and need a portable container without serverless size or timeout limits.
- **Decision:** Run the API container behind an Application Load Balancer on ECS Fargate. The same image can run worker commands.
- **Positive consequences:** File processing and long jobs fit the runtime; local Docker matches the shape of AWS.
- **Negative consequences:** Baseline cost is higher than a sporadic Lambda. Dev stays small to limit spend.
- **Alternatives:** Lambda plus a separate worker. Rejected: upload and job limits.
- **Affected plans / requirements:** Plans 08, 10; FR-OPS-001–004; R-06.

## ADR-006 — PostgreSQL with row-level security

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Application checks are necessary but not sufficient against a missed filter or a compromised query.
- **Decision:** Authorize in the use case, then enforce tenant isolation with PostgreSQL RLS. Transactions set tenant GUCs; the runtime role cannot bypass RLS.
- **Positive consequences:** Cross-tenant reads fail even if application code omits a filter.
- **Negative consequences:** Tests need real runtime and migration roles; every transaction must set tenant context.
- **Alternatives:** Application filters only. Rejected: a single missed `organization_id` would leak data.
- **Affected plans / requirements:** Plan 06; NFR-SEC-003–004; AC-011–013.

## ADR-007 — Ports for storage, identity, and AI

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Local development and tests must not require AWS accounts or live models.
- **Decision:** Hide S3, identity, and AI behind ports. Local adapters cover filesystem, dev auth, and a deterministic stub; AWS adapters cover S3, OIDC, and Bedrock.
- **Positive consequences:** Domain and use cases stay free of AWS SDKs; CI can run offline.
- **Negative consequences:** More adapter code at the start.
- **Alternatives:** Call AWS SDKs from use cases. Rejected: local and test environments would need cloud credentials.
- **Affected plans / requirements:** Plans 00, 05, 06; NFR-MNT-005.

## ADR-008 — Terraform state in S3 with a native lockfile

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** State needs remote locking. HashiCorp now supports native S3 lockfiles and treats a dedicated DynamoDB lock table as legacy.
- **Decision:** Keep state in a versioned, encrypted S3 bucket with `use_lockfile = true`. Do not create a new DynamoDB table for locking. Pin Terraform to 1.10 or newer (repository pin: 1.13.5).
- **Positive consequences:** One less AWS service and a lock mechanism that matches current Terraform.
- **Negative consequences:** Older Terraform cannot use this backend. A repo that still has a DynamoDB lock must migrate before applying.
- **Alternatives:** New DynamoDB lock table. Rejected: deprecated by current Terraform documentation.
- **Affected plans / requirements:** Plans 08–10; NFR-MNT-006; NFR-SEC-001–002.

If an older root still uses DynamoDB locking, upgrade Terraform to the pinned version, add `use_lockfile = true` next to the existing `dynamodb_table` argument, apply once so both locks exist, then remove the DynamoDB argument and the table in a later change.

## ADR-009 — CI assumes AWS through GitHub OIDC

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Permanent access keys in GitHub secrets are a standing credential risk.
- **Decision:** CI federates to a scoped AWS role with repository, branch, and environment conditions. Do not store `AWS_ACCESS_KEY_ID` or secret keys for deploy.
- **Positive consequences:** Short-lived credentials and least-privilege assume-role.
- **Negative consequences:** GitHub and AWS identity must be wired once before the first real deploy.
- **Alternatives:** Long-lived IAM users in Actions secrets. Rejected: rotation and leak risk.
- **Affected plans / requirements:** Plans 09–10; NFR-SEC-002; NFR-SEC-006.

## ADR-010 — One functional currency and monthly periods in 1.0

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Multi-currency and 4-4-5 calendars expand the import and analytics surface without a 1.0 demo need.
- **Decision:** Each organization has one functional currency. Periods are calendar months. The fiscal year start month is configurable. Import rows in another currency are rejected.
- **Positive consequences:** Simpler validation, totals, and display.
- **Negative consequences:** Multi-currency and 4-4-5 stay out of release 1.0 (BL-1104, BL-1105).
- **Alternatives:** Ship exchange rates or 4-4-5 now. Rejected: out of scope for 1.0.
- **Affected plans / requirements:** Plans 01–03; FR-DIM-001–003; BL-1104; BL-1105.

## ADR-011 — Interchangeable import execution

- **Status:** accepted
- **Date:** 2026-08-30
- **Context:** Import work must survive the HTTP request and run the same code locally and on AWS.
- **Decision:** Hide execution behind `ImportExecutor`. Local modes are inline or a process/CLI worker. AWS can invoke the same image as an ECS task or a dedicated worker later.
- **Positive consequences:** Job state lives in the database, not in request memory.
- **Negative consequences:** Operators must run or schedule the worker path for long jobs.
- **Alternatives:** Process imports only inside the request. Rejected: timeouts and lost work.
- **Affected plans / requirements:** Plans 02, 07, 10; FR-IMP-001–008; NFR-REL-004.

## ADR-012 — Conversation persistence policy

- **Status:** proposed
- **Date:** 2026-08-30
- **Context:** Copilot messages may contain financial questions. Storing full plaintext in production is a privacy decision that a human must make. Encryption at rest versus limited or redacted content is still open.
- **Decision:** Pending. Local and test environments may persist full synthetic conversation text. `dev` and `prod` persist a redacted placeholder until this ADR is accepted. Real customer data remains blocked by M-08 in [GATES.md](GATES.md).
- **Positive consequences:** Local demos keep a usable history. Production cannot silently store full chat text.
- **Negative consequences:** Production conversation history is not recoverable as prose until a human accepts a persistence policy.
- **Alternatives:** Accept full encrypted storage or redacted storage now. Deferred: needs a product and privacy decision.
- **Affected plans / requirements:** Plans 05, 10, 11; NFR-PRI-001–002; NFR-PRI-004; M-08.

## ADR-013 — Portable in-process metrics and W3C traces

- **Status:** accepted
- **Date:** 2026-09-03
- **Context:** The API must expose latency, errors, pool, job, and AI series without high-cardinality tenant labels, and every request must carry a trace identifier. A CloudWatch or OpenTelemetry SDK would add a vendor runtime to the local image.
- **Decision:** Keep a process-local metrics registry with route-template labels and hashed identifiers in JSON logs. Accept a valid W3C `traceparent` or generate a trace id, and return `X-Trace-Id`. Estimated AI cost is emitted only when a price table is configured and is labeled as an estimate.
- **Positive consequences:** The local image stays free of AWS telemetry SDKs. Tests can capture logs and snapshots. CloudWatch can still scrape or ingest the same JSON later.
- **Negative consequences:** Multi-task aggregation is the operations platform's job, not the API process. Cardinality must stay constrained in this registry.
- **Alternatives:** Embed OpenTelemetry or the CloudWatch SDK. Rejected for the local release candidate: extra dependencies without a measured need.
- **Affected plans / requirements:** Plan 07; NFR-OBS-001–004; NFR-MNT-005.

## Template

```text
## ADR-NNN — Title

- Status:
- Date:
- Context:
- Decision:
- Positive consequences:
- Negative consequences:
- Alternatives:
- Affected plans / requirements:
```
