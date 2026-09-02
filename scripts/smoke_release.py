#!/usr/bin/env python3
"""Post-deploy smoke checks. Never prints tokens, fixtures, or database URLs."""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

DIGEST_OR_SHA = re.compile(r"[0-9a-f]{7,40}", re.I)
SECRET_BODY_RE = re.compile(
    r"(AKIA[0-9A-Z]{16}|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|"
    r"postgresql(?:\+psycopg)?://|Bearer\s+[A-Za-z0-9._-]+|"
    r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)",
    re.I,
)
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})

SMOKE_STEPS: tuple[dict[str, str], ...] = (
    {"id": "cloudfront_https", "summary": "CloudFront or web loads over HTTPS"},
    {"id": "login_logout_cognito", "summary": "Cognito login and logout"},
    {"id": "organization_selector", "summary": "Organization selector"},
    {"id": "health_live", "summary": "GET /health/live"},
    {"id": "health_ready", "summary": "GET /health/ready"},
    {"id": "version", "summary": "GET /version matches the expected commit"},
    {"id": "synthetic_import", "summary": "Small synthetic import"},
    {"id": "dashboard_variance", "summary": "Dashboard and variance endpoints"},
    {"id": "cross_tenant_negative", "summary": "Cross-tenant negative check with demo users"},
    {"id": "copilot_or_stub", "summary": "Copilot stub, or Bedrock with AI-E01"},
    {"id": "audit_trace_id", "summary": "Audit or X-Trace-Id is present"},
    {"id": "logs_omit_secrets", "summary": "Responses omit fixture raw cells and tokens"},
)


Fetcher = Callable[[str, Mapping[str, str] | None], tuple[int, dict[str, str], str]]


def render_checklist() -> str:
    lines = [
        "# Release smoke",
        "",
        "Human steps stay human. Automated checks never store tokens.",
        "",
    ]
    for item in SMOKE_STEPS:
        lines.append(f"- [ ] {item['summary']}")
    lines.append("")
    return "\n".join(lines)


def application_uses_https(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return True
    host = (parsed.hostname or "").lower()
    return host in LOCAL_HOSTS


def reject_secrets(text: str) -> None:
    if SECRET_BODY_RE.search(text):
        raise ValueError("response body looks like a secret, token, or fixture raw value")


def require_trace_id(headers: Mapping[str, str]) -> str:
    for key, value in headers.items():
        if key.lower() == "x-trace-id" and value.strip():
            return value.strip()
    raise ValueError("X-Trace-Id is required")


def check_live(payload: Mapping[str, Any]) -> None:
    if payload.get("status") != "ok":
        raise ValueError("liveness must report status ok")


def check_ready(payload: Mapping[str, Any]) -> None:
    if payload.get("status") != "ready":
        raise ValueError("readiness must report status ready")


def check_version(payload: Mapping[str, Any], expected_commit: str = "") -> None:
    commit = str(payload.get("commit") or "")
    if not commit or commit == "unknown":
        raise ValueError("version commit is missing")
    if expected_commit and expected_commit not in commit:
        raise ValueError("version commit does not match the expected commit")
    if DIGEST_OR_SHA.search(commit) is None and expected_commit:
        raise ValueError("version commit is not identifiable")


def derive_version_url(health_url: str) -> str:
    if health_url.endswith("/health/ready"):
        return health_url[: -len("/health/ready")] + "/version"
    if health_url.endswith("/health/ready/"):
        return health_url[: -len("/health/ready/")] + "/version"
    return urljoin(health_url, "version")


def derive_live_url(health_url: str) -> str:
    if "/health/ready" in health_url:
        return health_url.replace("/health/ready", "/health/live")
    return urljoin(health_url, "live")


def default_fetch(
    url: str, headers: Mapping[str, str] | None = None
) -> tuple[int, dict[str, str], str]:
    request = Request(url, headers=dict(headers or {}), method="GET")
    context = ssl.create_default_context()
    try:
        with urlopen(request, timeout=20, context=context) as response:
            body = response.read().decode("utf-8")
            mapped = {str(key): str(value) for key, value in response.headers.items()}
            return int(response.status), mapped, body
    except HTTPError as error:
        body = error.read().decode("utf-8") if error.fp else ""
        mapped = {str(key): str(value) for key, value in error.headers.items()}
        return int(error.code), mapped, body
    except URLError as error:
        raise ValueError(f"request failed: {url}: {error}") from error


def evaluate_public_smoke(
    *,
    application_url: str,
    live: Mapping[str, Any],
    ready: Mapping[str, Any],
    version: Mapping[str, Any],
    headers: Mapping[str, str],
    expected_commit: str = "",
    bodies: Sequence[str] = (),
) -> dict[str, str]:
    if application_url and not application_uses_https(application_url):
        raise ValueError("application URL must use HTTPS outside localhost")
    check_live(live)
    check_ready(ready)
    check_version(version, expected_commit)
    trace_id = require_trace_id(headers)
    for body in bodies:
        reject_secrets(body)
    return {
        "cloudfront_https": "passed" if application_url else "skipped",
        "health_live": "passed",
        "health_ready": "passed",
        "version": str(version.get("commit") or ""),
        "audit_trace_id": trace_id,
        "logs_omit_secrets": "passed",
    }


def evaluate_authenticated_smoke(
    *,
    organizations: Sequence[Mapping[str, Any]],
    dashboard: Mapping[str, Any],
    variance: Mapping[str, Any],
    cross_tenant_status: int,
    copilot: Mapping[str, Any] | None,
    ai_provider: str = "stub",
) -> dict[str, str]:
    if not organizations:
        raise ValueError("organization selector returned no memberships")
    if "totals" not in dashboard and "items" not in dashboard:
        raise ValueError("dashboard payload is missing")
    if "items" not in variance and "totals" not in variance:
        raise ValueError("variance payload is missing")
    if cross_tenant_status not in {403, 404}:
        raise ValueError("cross-tenant check must return 403 or 404")
    if ai_provider == "stub":
        copilot_state = "stub"
    elif copilot and copilot.get("grounded") is not False:
        copilot_state = "bedrock"
    else:
        raise ValueError("copilot must stay stub or answer AI-E01 with grounding")
    return {
        "organization_selector": "passed",
        "dashboard_variance": "passed",
        "cross_tenant_negative": str(cross_tenant_status),
        "copilot_or_stub": copilot_state,
        "synthetic_import": "manual-or-optional",
        "login_logout_cognito": "human",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-checklist", action="store_true")
    parser.add_argument("--api-health-url")
    parser.add_argument("--application-url", default="")
    parser.add_argument("--version-url", default="")
    parser.add_argument("--expected-commit", default="")
    parser.add_argument("--attempts", type=int, default=20)
    parser.add_argument("--delay-seconds", type=int, default=15)
    args = parser.parse_args(argv)

    if args.print_checklist:
        print(render_checklist(), end="")
        if not args.api_health_url:
            return 0
    if not args.api_health_url:
        parser.error("--api-health-url is required unless --print-checklist")

    import time

    live_url = derive_live_url(args.api_health_url)
    version_url = args.version_url or derive_version_url(args.api_health_url)
    last_error = "readiness did not succeed"
    for attempt in range(1, args.attempts + 1):
        try:
            ready_status, ready_headers, ready_body = default_fetch(args.api_health_url)
            reject_secrets(ready_body)
            ready_payload = json.loads(ready_body)
            if ready_status == 200 and isinstance(ready_payload, dict):
                check_ready(ready_payload)
                live_status, live_headers, live_body = default_fetch(live_url)
                reject_secrets(live_body)
                live_payload = json.loads(live_body)
                if live_status != 200 or not isinstance(live_payload, dict):
                    raise ValueError("liveness request failed")
                check_live(live_payload)
                version_status, version_headers, version_body = default_fetch(version_url)
                reject_secrets(version_body)
                version_payload = json.loads(version_body)
                if version_status != 200 or not isinstance(version_payload, dict):
                    raise ValueError("version request failed")
                if args.application_url:
                    app_status, _app_headers, app_body = default_fetch(args.application_url)
                    reject_secrets(app_body)
                    if app_status >= 400:
                        raise ValueError("application URL did not load")
                headers = {**ready_headers, **live_headers, **version_headers}
                result = evaluate_public_smoke(
                    application_url=args.application_url,
                    live=live_payload,
                    ready=ready_payload,
                    version=version_payload,
                    headers=headers,
                    expected_commit=args.expected_commit,
                    bodies=(ready_body, live_body, version_body),
                )
                print(json.dumps(result, indent=2))
                print(render_checklist(), end="")
                return 0
            last_error = f"readiness status {ready_status}"
        except (ValueError, json.JSONDecodeError) as error:
            last_error = str(error)
        if attempt == args.attempts:
            print(last_error, file=sys.stderr)
            return 1
        time.sleep(args.delay_seconds)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
