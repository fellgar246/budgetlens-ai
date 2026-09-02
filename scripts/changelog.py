#!/usr/bin/env python3
"""Generate a SemVer changelog fragment from commits or pull request titles."""

from __future__ import annotations

import argparse
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBJECT_RE = re.compile(r"^[0-9a-f]{7,40}\s+(.*)$")


def semver_from_ref(ref: str) -> str:
    value = ref.rsplit("/", 1)[-1]
    if value.startswith("v") and re.fullmatch(r"v\d+\.\d+\.\d+", value):
        return value[1:]
    if re.fullmatch(r"\d+\.\d+\.\d+", value):
        return value
    raise ValueError(f"{ref} is not a SemVer tag")


def parse_subjects(git_log: str) -> list[str]:
    subjects: list[str] = []
    for line in git_log.splitlines():
        match = SUBJECT_RE.match(line.strip())
        if match:
            subject = match.group(1).strip()
            if subject and not subject.lower().startswith("merge "):
                subjects.append(subject)
    return subjects


def render_changelog(version: str, subjects: Sequence[str], previous: str = "") -> str:
    heading = f"## {version}"
    if previous:
        heading += f" <!-- previous: {previous} -->"
    if not subjects:
        body = "- Maintenance release."
    else:
        body = "\n".join(f"- {subject}" for subject in subjects)
    return f"{heading}\n\n{body}\n"


def git_log(range_spec: str) -> str:
    result = subprocess.run(
        ["git", "log", "--pretty=format:%h %s", range_spec],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version")
    parser.add_argument("--ref", default="")
    parser.add_argument("--range", default="")
    parser.add_argument("--subjects-file", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    version = args.version or (semver_from_ref(args.ref) if args.ref else "unreleased")
    if args.subjects_file:
        subjects = parse_subjects(args.subjects_file.read_text(encoding="utf-8"))
    elif args.range:
        subjects = parse_subjects(git_log(args.range))
    else:
        subjects = []
    text = render_changelog(version, subjects)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
