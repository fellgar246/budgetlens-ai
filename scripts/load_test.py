#!/usr/bin/env python3
"""Measure local read latency against a running API. Does not print financial rows."""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
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


def json_get(url: str, headers: dict[str, str]) -> object:
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_version_id(base_url: str, headers: dict[str, str], requested: str) -> str:
    if requested:
        return requested
    payload = json_get(f"{base_url}/api/v1/budget-versions?limit=50", headers)
    if not isinstance(payload, dict):
        raise SystemExit("budget version list is not an object")
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise SystemExit("seed a budget version before measuring reads")
    for raw in items:
        if not isinstance(raw, dict):
            continue
        if raw.get("name") == "Budget Final":
            return str(raw["id"])
    first = items[0]
    if isinstance(first, dict):
        return str(first["id"])
    raise SystemExit("could not resolve a budget version")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--token", default="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1")
    parser.add_argument(
        "--organization-id", default="11111111-1111-4111-8111-111111111111"
    )
    parser.add_argument("--budget-version-id", default="")
    parser.add_argument("--fiscal-year", type=int, default=2026)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--output", type=Path, default=Path("var/perf/read-baseline.json"))
    args = parser.parse_args()
    headers = {
        "Authorization": f"Bearer {args.token}",
        "X-Organization-Id": args.organization_id,
    }
    version_id = resolve_version_id(args.base_url, headers, args.budget_version_id)
    query = urllib.parse.urlencode(
        {
            "fiscal_year": args.fiscal_year,
            "period_from": f"{args.fiscal_year}-01-01",
            "period_to": f"{args.fiscal_year}-12-01",
            "budget_version_id": version_id,
        }
    )
    url = f"{args.base_url}/api/v1/analytics/variance-summary?{query}"
    samples = [timed_get(url, headers) for _ in range(args.iterations)]
    p95 = percentile(samples, 0.95)
    payload = {
        "measured_at": datetime.now(UTC).isoformat(),
        "iterations": args.iterations,
        "fiscal_year": args.fiscal_year,
        "p50_ms": percentile(samples, 0.50),
        "p95_ms": p95,
        "mean_ms": int(statistics.mean(samples)),
        "target_p95_ms": 500,
        "passed": p95 < 500,
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
