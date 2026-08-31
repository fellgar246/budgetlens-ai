#!/usr/bin/env python3
"""Measure local read latency against a running API. Does not print financial rows."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path


def timed_get(url: str, headers: dict[str, str]) -> int:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        response.read()
        status = response.status
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    if status >= 400:
        raise RuntimeError(f"request failed with {status}")
    return elapsed_ms


def percentile(samples: list[int], ratio: float) -> int:
    if not samples:
        return 0
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * ratio) - 1))
    return ordered[index]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", required=True)
    parser.add_argument("--organization-id", required=True)
    parser.add_argument("--budget-version-id", required=True)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("var/perf/read-baseline.json"))
    args = parser.parse_args()
    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Organization-Id": args.organization_id,
    }
    url = (
        f"{args.base_url}/api/v1/analytics/variance-summary"
        f"?fiscal_year=2026&period_from=2026-01-01&period_to=2026-12-01"
        f"&budget_version_id={args.budget_version_id}"
    )
    samples = [timed_get(url, headers) for _ in range(args.iterations)]
    payload = {
        "iterations": args.iterations,
        "p50_ms": percentile(samples, 0.50),
        "p95_ms": percentile(samples, 0.95),
        "mean_ms": int(statistics.mean(samples)),
        "target_p95_ms": 500,
        "passed": percentile(samples, 0.95) < 500,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload))
    if not payload["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"API is not reachable: {exc}") from exc
