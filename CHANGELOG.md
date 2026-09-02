# Changelog

Application releases use SemVer (`vMAJOR.MINOR.PATCH`). Generate a fragment from commits with `python scripts/changelog.py --ref vX.Y.Z --range <previous>..HEAD`.

## Unreleased

- Local portfolio demo: product README, architecture diagrams, 6–8 minute walkthrough, synthetic sample-data guide, sanitized stub AI eval aggregate, dated Terraform sizes without an invented bill, and a release checklist that refuses `v1.0.0` until production gates are recorded.
- AWS deployment runbook: preflight, bootstrap, plan/apply guards, smoke, explicit demo seed, observation, rollback, isolated restore, and teardown.
- CI/CD workflows for path-filtered CI, image publish, Terraform plan, and environment deploys.
- Cost and operations guardrails: dated official estimates, account budget and anomaly controls, visible Terraform sizes, and teardown/runbooks.
- Manual gates M-00–M-10: documented human checklists, secret-free records, and apply review that code cannot assume.
