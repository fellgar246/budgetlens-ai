# Manual gates

These are the only decisions the code must not assume. Everything else can be implemented and verified locally with synthetic data, stubs, and static Terraform checks.

A gate is a human action or policy. Terraform, CI, and the API may expose variables and conservative defaults. They must not invent an account, region, model, domain, user policy, or production cutover.

Record completions without secrets:

```text
python scripts/record_gate.py --list
python scripts/record_gate.py --print-checklist M-09
make record-gate GATE=M-01 ENVIRONMENT=dev RECORDED_BY='<human>' \
  DELIVERABLES='aws_account_id=123456789012 credential_method=sso profile_or_role=budgetlens-admin'
make check-gates SCOPE=apply ENVIRONMENT=dev
make review-apply ENVIRONMENT=dev RECORDED_BY='<human>' ACCOUNT='<id>' ROLE='<role>' \
  REGION='us-east-1' IMAGE_DIGEST='repo@sha256:…' CONFIRM=1
```

Files land in `var/gates/` (gitignored). GitHub repository variables may satisfy M-01 and M-02 for a real remote plan. They are not a substitute for the apply checklist.

## Gate M-00 — Functional defaults

**When:** before or during Plan 01.  
**Owner:** Domain owner.  
**Local simulation:** yes. Defaults do not block implementation.  
**Blocks:** nothing if the spec defaults stay accepted.

Confirm or accept:

| Decision | Default in this repository |
|---|---|
| Fiscal year | Calendar months. Start month is configurable. Demo: Alpha January, Beta April. |
| Demo currency | One functional currency per organization. Demo: Alpha MXN, Beta USD. |
| Favorability | Expense over budget is unfavorable. Revenue over budget is favorable. |
| Actuals | Each import batch accumulates. Explicit range replace is deferred (BL-1102). |
| Product language | Spanish product copy. Repository documentation stays English. |

## Gate M-01 — Secure AWS account

**When:** before a real `terraform plan`.  
**Owner:** Security owner.  
**Local simulation:** no. Static `fmt`/`validate` does not need an account.  
**Blocks:** AWS.

Outside the IDE:

- create or select the account and payment method;
- enable root MFA;
- do not use root for deploys;
- configure IAM Identity Center or an equivalent administrative identity;
- record the AWS account ID;
- define owner and cost-center tags.

**Deliverables to the repository:** account ID, how temporary credentials are obtained (`sso`, `oidc`, `assumed_role`, or `identity_center`), and the profile or role name. Never paste secret keys in Markdown or Git.

Committed `terraform.tfvars` leave `aws_account_id` empty until this gate is recorded.

## Gate M-02 — Region

**When:** before remote bootstrap.  
**Owner:** Operator.  
**Local simulation:** fake config.  
**Blocks:** AWS.

Evaluate Bedrock availability for the chosen model, other services, residency, latency, price, and ACM/CloudFront constraints.

**Deliverable:** primary region. Record an ADR if the choice changes architecture.

## Gate M-03 — Budget and alerts

**When:** before apply.  
**Owner:** Operator.  
**Local simulation:** Terraform can create the budget and SNS topic.  
**Blocks:** AWS.

- choose the limit and thresholds;
- name the alert email or SNS target;
- confirm the subscription email when AWS sends it;
- review a dated official estimate (`scripts/record_cost_estimate.py`).

A budget is an alert, not a hard cap. Reception and confirmation stay human.

## Gate M-04 — Bedrock model access

**When:** live evaluation and AWS AI (Plans 05 and 10).  
**Owner:** AI owner.  
**Local simulation:** stub provider and contract tests.  
**Blocks:** AWS AI, not local work.

- select a model that supports the required tool use;
- accept terms or request access if the account or region requires it;
- record the exact model ID as `BEDROCK_MODEL_ID` / `bedrock_model_id`;
- run live evaluation and approve results and cost.

Do not hardcode a commercial model name in domain or use-case code. Keep `ai_provider=stub` until this gate is complete.

## Gate M-05 — GitHub repository and OIDC

**When:** Plan 09, before the real pipeline deploys.  
**Owner:** Engineering.  
**Local simulation:** workflow lint.  
**Blocks:** the real pipeline.

- create or select the remote repository;
- record the exact `owner/name`;
- enable branch protection;
- create GitHub Environments `dev` and `prod` with reviewers;
- allow OIDC and Actions according to repository policy.

Terraform can create the AWS OIDC provider and roles. Repository settings still need owner permissions. Do not store `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`.

## Gate M-06 — Domain and DNS

**When:** optional for development; required before a final production URL.  
**Owner:** Operator.  
**Local simulation:** CloudFront and Cognito managed domains.  
**Blocks:** production URL.

- buy or select the domain;
- choose Route 53 or an external DNS provider;
- authorize ACM and Cognito validation records;
- define callback and logout URLs.

## Gate M-07 — User policy

**When:** before enabling Cognito for third parties.  
**Owner:** Security owner.  
**Local simulation:** local `AUTH_MODE=dev` and test JWKS.  
**Blocks:** third-party users.

- open registration versus invitation;
- MFA required or optional;
- account recovery;
- first admin process;
- terms and privacy if external users will sign in.

`allow_self_registration` stays `false` until this gate is recorded. Terraform does not create users.

## Gate M-08 — Data and conversation policy

**When:** before real data or production.  
**Owner:** Product/Security.  
**Local simulation:** synthetic seed and redacted cloud storage.  
**Blocks:** real customer data.

- classification and residency;
- retention for uploads, exports, audit, and chat;
- whether full conversation text is stored;
- operator access;
- deletion and export.

This gate accepts [ADR-012](DECISIONS.md). Until then, `dev` and `prod` persist a redacted placeholder. Local and test may keep full synthetic text.

## Gate M-09 — Apply review

**When:** Plan 10, immediately before apply.  
**Owner:** Operator.  
**Local simulation:** no.  
**Blocks:** AWS apply.

Review, then authorize:

- AWS identity (`account`, `role`, `region`);
- the Terraform plan, especially destroys and replacements;
- the dated estimate and expensive resources;
- the image digest;
- the migration;
- DNS and callback URLs.

Production apply is never `terraform apply -auto-approve` without a plan file from the same job. GitHub Environment reviewers are the remote authorization. Locally, `make review-apply CONFIRM=1` records this gate after the checklist.

## Gate M-10 — Production

**When:** Plan 11. Outside the minimum portfolio cutover.  
**Owner:** Owner.  
**Local simulation:** no.  
**Blocks:** production.

Requires a production account or environment, threat and privacy review, restore test, live AI evaluation when Bedrock is enabled, incident ownership, and an approved plan and window.

## Information that must never be requested

A plan, pull request, chat, or spec must never ask for:

- AWS root password
- secret access key pasted in chat or Git
- production database password
- Cognito token
- real financial file contents
- complete Terraform plan or state with sensitive values

Allowed inputs are account IDs, region names, role or profile names, model IDs, GitHub `owner/name`, public callback URLs, and dated official estimates. Those are not secrets.

## Scope checks

| Scope | Required recorded gates |
|---|---|
| `local` | None. M-00 defaults apply. |
| `plan` | M-01, M-02 |
| `apply` | M-01, M-02, M-03, M-09 |
| `aws` | M-01, M-02, M-03, M-05, M-09 |
| `prod` | M-01, M-02, M-03, M-05, M-06, M-07, M-08, M-09, M-10 |

M-04 is required only when `ai_provider=bedrock`. M-06 may be waived for development. M-07 and M-08 stay waived while self-registration is off and only synthetic data is used; enabling third-party users or real data requires a human record.

See [TRACEABILITY.md](TRACEABILITY.md) for owners and release blockers, [OPERATIONS.md](OPERATIONS.md) for cost and apply runbooks, and [CICD.md](CICD.md) for OIDC.
