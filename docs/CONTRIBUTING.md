# Contributing

Code, identifiers, comments, and repository documentation are written in English. User-visible product copy stays in Spanish and lives in `apps/web/src/lib/copy.ts` (web) or domain/HTTP error messages (API).

## Toolchain

Use the versions in `.python-version`, `.node-version`, `package.json` `packageManager`, `apps/api/pyproject.toml`, and `infrastructure/terraform/.terraform-version`. Python type checking is **Pyright** in strict mode. The IaC scanner is **Checkov**; Terraform lint is **TFLint**. Pins: `infrastructure/terraform/.checkov-version` and `.tflint-version`.

Do not add a dependency unless it provides a capability the standard library cannot, and record the version range in the lockfile. Domain code must not import boto, FastAPI, SQLAlchemy, or an identity SDK.

Automated update PRs are welcome. Major-version PRs are reviewed by a human and are never auto-merged.

## Git

- Default branch: `main` (protected).
- Branch names: `codex/<topic>` or `<type>/<topic>` (for example `fix/import-timeout`).
- Commits are small and use the imperative mood.
- Do not version `.env`, credentials, Terraform plans or state, uploads, exports, or real financial files.

Every pull request names the requirement and plan it implements:

```text
Implements FR-IMP-001; Plan 02
```

A change to `packages/api-client/openapi.json` needs an explicit review. That file is generated (`make openapi`) and is not edited by hand. The TypeScript client is validated against the snapshot.

## Configuration

Precedence: safe defaults, then the untracked local `.env`, then process environment variables, then Secrets Manager for secrets on AWS. Every new setting is added to `.env.example` with description, type, secrecy, and applicable environments.

## Definition of done

- Requirement and acceptance are identified in the PR trailer.
- Code and migrations (if any) are implemented.
- Types, lint, and format are clean.
- Positive, edge, and negative tests cover the change.
- Errors stay safe; add telemetry when the change is observable.
- Documentation and `.env.example` are updated in English.
- No secrets or real data.
- The diff has been reviewed.
- Exact commands and results are reported in the PR.
