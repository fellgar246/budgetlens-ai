## Summary

Implements FR-XXX-000; Plan NN

<!-- Replace the trailer with the requirement and plan this change delivers. -->

## Checklist

- [ ] Types, lint, and format are clean (`make lint`)
- [ ] Unit tests pass (`make test`); integration tests if the change touches persistence (`make test-integration`)
- [ ] Contract tests if the HTTP surface changed (`make test-contract`)
- [ ] A regression test is added for every bug fix
- [ ] OpenAPI snapshot reviewed if `packages/api-client/openapi.json` changed (`make openapi`)
- [ ] `.env.example` updated for any new setting
- [ ] No secrets, credentials, Terraform state, uploads, or real financial files

## Test plan

-
