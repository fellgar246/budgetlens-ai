from __future__ import annotations

import sys

from budgetlens.seed import run_seed


def main(argv: list[str] | None = None) -> None:
    args = argv if argv is not None else sys.argv[1:]
    if args == ["seed"]:
        run_seed()
        print("Seed applied.")
        return
    raise SystemExit("Usage: python -m budgetlens seed")
