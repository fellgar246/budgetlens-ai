#!/usr/bin/env python3
"""Generate a synthetic 250k-row CSV for local read-path measurements."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=250_000)
    parser.add_argument("--output", type=Path, default=Path("var/perf/250k-actuals.csv"))
    parser.add_argument(
        "--near-limit",
        action="store_true",
        help="Generate a file just under the 100k-row import limit (not versioned).",
    )
    args = parser.parse_args()
    if args.near_limit:
        args.rows = 99_000
        if args.output == Path("var/perf/250k-actuals.csv"):
            args.output = Path("var/perf/near-limit-import.csv")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    accounts = ("6100", "6200", "4100", "5100")
    departments = ("OPS", "FIN", "MKT", "IT")
    with args.output.open("w", encoding="utf-8") as handle:
        handle.write("period,account_code,department_code,amount,currency\n")
        for index in range(args.rows):
            month = (index % 12) + 1
            account = accounts[index % len(accounts)]
            department = departments[index % len(departments)]
            amount = f"{(index % 500) + 1}.0000"
            handle.write(f"2026-{month:02d},{account},{department},{amount},MXN\n")
    print(args.output)


if __name__ == "__main__":
    main()
