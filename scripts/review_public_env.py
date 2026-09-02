#!/usr/bin/env python3
"""Reject frontend public build values that look like secrets."""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections.abc import Mapping, Sequence

ALLOWED_PUBLIC_KEYS = frozenset(
    {
        "NEXT_PUBLIC_API_BASE_URL",
        "NEXT_PUBLIC_APP_ENV",
    }
)
ALLOWED_APP_ENVS = frozenset({"local", "test", "dev", "production"})
SECRET_VALUE_RE = re.compile(
    r"AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|aws_secret_access_key|password=|://[^/\s]+:[^/\s]+@",
    re.I,
)


def public_env_from_mapping(values: Mapping[str, str]) -> dict[str, str]:
    return {key: value for key, value in values.items() if key.startswith("NEXT_PUBLIC_")}


def review_public_env(values: Mapping[str, str]) -> list[str]:
    offenders: list[str] = []
    for key, value in public_env_from_mapping(values).items():
        if key not in ALLOWED_PUBLIC_KEYS:
            offenders.append(f"{key} is not an approved public frontend variable")
            continue
        if SECRET_VALUE_RE.search(value):
            offenders.append(f"{key} looks like a secret")
            continue
        if key == "NEXT_PUBLIC_APP_ENV" and value not in ALLOWED_APP_ENVS:
            offenders.append(f"{key} must be one of {sorted(ALLOWED_APP_ENVS)}")
        if key == "NEXT_PUBLIC_API_BASE_URL" and value and not (
            value.startswith("http://") or value.startswith("https://")
        ):
            offenders.append(f"{key} must be an http(s) URL")
    return offenders


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("assignments", nargs="*", help="KEY=VALUE pairs. Defaults to process env.")
    args = parser.parse_args(argv)
    if args.assignments:
        values = {}
        for item in args.assignments:
            key, sep, value = item.partition("=")
            if not sep:
                raise SystemExit(f"Expected KEY=VALUE, got {item!r}")
            values[key] = value
    else:
        values = {key: str(value) for key, value in os.environ.items()}
    offenders = review_public_env(values)
    if offenders:
        sys.stderr.write("\n".join(offenders) + "\n")
        return 1
    print("Public frontend environment is not secret.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
