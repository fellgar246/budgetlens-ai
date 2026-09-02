# Changelog

Application releases use SemVer (`vMAJOR.MINOR.PATCH`). Generate a fragment from commits with `python scripts/changelog.py --ref vX.Y.Z --range <previous>..HEAD`.

## Unreleased

- AWS deployment runbook: preflight, bootstrap, plan/apply guards, smoke, explicit demo seed, observation, rollback, isolated restore, and teardown.
- CI/CD workflows for path-filtered CI, image publish, Terraform plan, and environment deploys.
- Cost and operations guardrails: dated official estimates, account budget and anomaly controls, visible Terraform sizes, and teardown/runbooks.
- Manual gates M-00–M-10: documented human checklists, secret-free records, and apply review that code cannot assume.
