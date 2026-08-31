# Architecture decisions

Accepted decisions that affect the shape of the product. Do not rewrite an accepted row; add a new entry and mark the old one superseded.

| ID | Status | Decision |
|---|---|---|
| ADR-001 | Accepted | Modular monolith: one API deployable; workers reuse the same codebase |
| ADR-002 | Accepted | Deterministic financial calculations stay outside the LLM; the model only calls tools |
| ADR-003 | Accepted | PostgreSQL `numeric(19,4)`, Python `Decimal`, JSON amounts as strings |
| ADR-004 | Accepted | Next.js static export behind CloudFront; no required SSR |
| ADR-005 | Accepted | FastAPI on ECS Fargate behind an ALB |
| ADR-006 | Accepted | Application authorization plus PostgreSQL row-level security |
| ADR-007 | Accepted | Ports for object storage, identity, and AI; local adapters for development |
| ADR-008 | Accepted | Terraform state in versioned/encrypted S3 with native lockfile; no new DynamoDB lock table |
| ADR-009 | Accepted | CI assumes AWS through GitHub OIDC; no permanent access keys |
| ADR-010 | Accepted | One functional currency and monthly periods in 1.0 |
| ADR-011 | Accepted | Import execution behind an interchangeable `ImportExecutor` |
| ADR-012 | Proposed | Conversation persistence policy (full encrypted text vs redacted). Local synthetic content is allowed; production waits for a human decision |

Irreversible or costly changes require a new row (NFR-MNT-006).
