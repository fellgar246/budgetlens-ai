#!/usr/bin/env python3
"""Write identifiable release evidence without secret values."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "commit",
    "tag",
    "image_digest",
    "terraform_plan",
    "migration_revision",
    "smoke_results",
    "ai_evaluation",
    "known_risks",
    "rollback_target",
)


def build_evidence(
    *,
    commit: str,
    tag: str = "",
    image_digest: str,
    terraform_plan: str,
    migration_revision: str,
    smoke_results: str,
    ai_evaluation: str,
    known_risks: str,
    rollback_target: str,
    app_version: str = "",
    environment: str = "",
) -> dict[str, Any]:
    if image_digest.endswith(":latest") or image_digest.endswith(":LATEST"):
        raise ValueError("image_digest must not use the latest tag")
    if image_digest and "@sha256:" not in image_digest and not image_digest.startswith("sha256:"):
        raise ValueError("image_digest must be a digest identity")
    return {
        "commit": commit,
        "tag": tag,
        "app_version": app_version,
        "environment": environment,
        "image_digest": image_digest,
        "terraform_plan": terraform_plan,
        "migration_revision": migration_revision,
        "smoke_results": smoke_results,
        "ai_evaluation": ai_evaluation,
        "known_risks": known_risks,
        "rollback_target": rollback_target,
    }


def render_markdown(evidence: dict[str, Any]) -> str:
    lines = ["# Release evidence", ""]
    for field in (
        *REQUIRED_FIELDS[:3],
        "app_version",
        "environment",
        *REQUIRED_FIELDS[3:],
    ):
        lines.append(f"- **{field}:** {evidence.get(field) or '(none)'}")
    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--tag", default="")
    parser.add_argument("--app-version", default="")
    parser.add_argument("--environment", default="")
    parser.add_argument("--image-digest", required=True)
    parser.add_argument("--terraform-plan", default="not-applied")
    parser.add_argument("--migration-revision", default="unknown")
    parser.add_argument("--smoke-results", default="not-run")
    parser.add_argument("--ai-evaluation", default="stub / not required")
    parser.add_argument("--known-risks", default="see docs/RISKS.md")
    parser.add_argument("--rollback-target", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    evidence = build_evidence(
        commit=args.commit,
        tag=args.tag,
        app_version=args.app_version,
        environment=args.environment,
        image_digest=args.image_digest,
        terraform_plan=args.terraform_plan,
        migration_revision=args.migration_revision,
        smoke_results=args.smoke_results,
        ai_evaluation=args.ai_evaluation,
        known_risks=args.known_risks,
        rollback_target=args.rollback_target,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    markdown = args.output.with_suffix(".md")
    markdown.write_text(render_markdown(evidence), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
