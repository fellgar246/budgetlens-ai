# Release checklist

Use this list before calling the local portfolio demo complete, before an AWS development apply, or before cutting a SemVer tag. Checkboxes that depend on human gates must stay unchecked until a recorded gate exists. Never paste secrets into a pull request or this file.

Application version in the tree is `0.1.0`. Tag `v1.0.0` is **blocked** until the `prod` gate set is recorded.

```text
make portfolio-check
```

`scripts/portfolio_release.py --tag` refuses unless those gates are present. Do not create `v1.0.0` by hand to skip the check.

## Local portfolio (no AWS)

- [x] Clean clone onboarding works: `make doctor`, `make bootstrap`, `make dev`, `make migrate`, `make seed` ([README.md](../README.md), AC-001)
- [x] Synthetic dataset only; no real ledgers versioned ([sample-data/README.md](../sample-data/README.md))
- [x] Demo script does not require private knowledge ([DEMO.md](DEMO.md))
- [x] Architecture matches Compose and Terraform modules ([ARCHITECTURE.md](ARCHITECTURE.md))
- [x] Stub AI eval 20/20 is the required suite result ([AI_EVALUATION.md](AI_EVALUATION.md))
- [x] Cost page lists sizes and refuses an invented price ([COST.md](COST.md))
- [x] Decisions and limitations are linked ([DECISIONS.md](DECISIONS.md), [BACKLOG.md](BACKLOG.md), [RISKS.md](RISKS.md))
- [x] Rollback and restore are documented ([OPERATIONS.md](OPERATIONS.md), [DEPLOYMENT.md](DEPLOYMENT.md), AC-025, AC-026)
- [x] Traceability maps requirement → test → implementation ([TRACEABILITY.md](TRACEABILITY.md))
- [ ] Optional UI screenshots from the seeded dataset ([screenshots/README.md](screenshots/README.md))

## AWS development (human gates)

- [ ] M-01 account and credential method
- [ ] M-02 region
- [ ] M-03 budget, alert email, dated official estimate
- [ ] M-04 Bedrock model, or stay on `ai_provider=stub`
- [ ] M-05 GitHub environments and OIDC variables
- [ ] M-07 / M-08 stay waived only while self-registration is off and data is synthetic
- [ ] M-09 apply review
- [ ] Smoke, observation, and isolated restore (`budgetlens-dev-restore`)
- [ ] Decision to keep development up or tear it down

Record gates with `make record-gate`. The code must not assume them.

## Production tag `v1.0.0`

- [ ] Every item in the AWS development list
- [ ] M-06 public URL or an explicit waiver for development-only hosting
- [ ] M-10 production cutover
- [ ] AC-001–AC-025 green on the intended environment
- [ ] AC-026 restore demonstrated if calling the product production-ready
- [ ] Changelog fragment for the tag (`python scripts/changelog.py`)
- [ ] Image digest identity (never `latest`)
- [ ] No secrets, account identifiers, or real financial files in the tag

Until that list is recorded, keep talking about a **local portfolio demo**, not a production release.

## After a tag (when unblocked)

1. Push `vMAJOR.MINOR.PATCH`.
2. Let `Build` publish the digest and `Deploy prod` run only through the protected environment.
3. Attach secret-free evidence: commit, digest, plan identity, migration revision, smoke, AI/model note, rollback target.
4. If development is no longer needed, follow teardown and keep state on purpose.
