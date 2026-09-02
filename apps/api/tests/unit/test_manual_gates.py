from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

import pytest
from tests.traceability_catalog import GATES

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS = REPO_ROOT / "scripts"
DOCS = REPO_ROOT / "docs"
API_SRC = REPO_ROOT / "apps" / "api" / "src" / "budgetlens"
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
COMMERCIAL_MODEL_NAMES = ("claude", "sonnet", "haiku", "anthropic", "titan", "nova-pro", "llama-3")
SECRET_REQUEST = re.compile(
    r"(enter|paste|provide|type) (your )?(aws )?"
    r"(root password|secret access key|database password|cognito token)",
    re.IGNORECASE,
)


def _load(name: str) -> ModuleType:
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gates_document_lists_every_gate_and_forbidden_inputs() -> None:
    text = (DOCS / "GATES.md").read_text(encoding="utf-8")
    gates = _load("record_gate")
    for gate_id in gates.GATE_IDS:
        assert gate_id in text, gate_id
    assert "## Information that must never be requested" in text
    for phrase in gates.FORBIDDEN_IN_PLANS:
        assert phrase in text, phrase
    assert "var/gates" in text
    assert "CONFIRM=1" in text
    assert ("spec" + "-docs") not in text


def test_gate_script_matches_catalog() -> None:
    gates = _load("record_gate")
    assert list(gates.GATE_SPECS) == [item["id"] for item in GATES]
    for item in GATES:
        spec = gates.GATE_SPECS[item["id"]]
        assert spec["name"] == item["name"]
        assert spec["owner"] == item["owner"]
        assert spec["moment"] == item["moment"]
        assert spec["local_simulation"] == item["local_simulation"]
        assert spec["blocks"] == item["blocks"]


def test_local_scope_does_not_require_cloud_gates() -> None:
    gates = _load("record_gate")
    assert gates.required_gates("local") == []
    assert gates.check_scope("local", "local") == []
    assert gates.required_gates("plan") == ["M-01", "M-02"]
    assert gates.required_gates("apply") == ["M-01", "M-02", "M-03", "M-09"]
    assert "M-10" in gates.required_gates("prod")
    assert "M-04" not in gates.required_gates("apply")
    assert "M-04" in gates.required_gates("apply", ai_provider="bedrock")


def test_functional_defaults_record_without_extra_deliverables() -> None:
    gates = _load("record_gate")
    record = gates.build_record(gate="M-00", recorded_by="Luis", environment="local")
    assert record["status"] == "complete"
    assert record["deliverables"]["product_language"].startswith("Spanish")
    assert record["deliverables"]["actuals_mode"].startswith("actuals accumulate")


def test_protected_gates_reject_agent_and_secrets() -> None:
    gates = _load("record_gate")
    with pytest.raises(ValueError, match="human recorded_by"):
        gates.build_record(
            gate="M-01",
            recorded_by="agent",
            environment="dev",
            deliverables={
                "aws_account_id": "123456789012",
                "credential_method": "sso",
                "profile_or_role": "budgetlens-admin",
            },
        )
    with pytest.raises(ValueError, match="placeholder"):
        gates.build_record(
            gate="M-01",
            recorded_by="Luis",
            environment="dev",
            deliverables={
                "aws_account_id": "000000000000",
                "credential_method": "sso",
                "profile_or_role": "budgetlens-admin",
            },
        )
    with pytest.raises(ValueError, match="forbidden"):
        gates.build_record(
            gate="M-01",
            recorded_by="Luis",
            environment="dev",
            deliverables={
                "aws_account_id": "123456789012",
                "credential_method": "sso",
                "profile_or_role": "budgetlens-admin",
                "secret_access_key": "never",
            },
        )
    with pytest.raises(ValueError, match="secret"):
        gates.reject_forbidden_deliverables({"notes": "AKIAIOSFODNN7EXAMPLE"})
    with pytest.raises(ValueError, match="root"):
        gates.build_record(
            gate="M-01",
            recorded_by="Luis",
            environment="dev",
            deliverables={
                "aws_account_id": "123456789012",
                "credential_method": "sso",
                "profile_or_role": "root",
            },
        )


def test_apply_review_requires_confirmation_and_digest() -> None:
    gates = _load("record_gate")
    with pytest.raises(ValueError, match="CONFIRM=1"):
        gates.build_apply_review(
            environment="dev",
            recorded_by="Luis",
            aws_account="123456789012",
            aws_role="github-deploy-dev",
            aws_region="us-east-1",
            image_digest="123.dkr.ecr.us-east-1.amazonaws.com/api@sha256:" + ("ab" * 32),
            confirm="",
        )
    record = gates.build_apply_review(
        environment="dev",
        recorded_by="Luis",
        aws_account="123456789012",
        aws_role="github-deploy-dev",
        aws_region="us-east-1",
        image_digest="123.dkr.ecr.us-east-1.amazonaws.com/api@sha256:" + ("ab" * 32),
        confirm="1",
    )
    assert record["gate"] == "M-09"
    assert record["confirmed"] is True
    first = gates.build_apply_review(
        environment="dev",
        recorded_by="Luis",
        aws_account="123456789012",
        aws_role="github-deploy-dev",
        aws_region="us-east-1",
        image_digest="",
        confirm="1",
        first_apply=True,
    )
    assert first["deliverables"]["image_digest"] == "first-apply"


def test_check_and_record_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    gates = _load("record_gate")
    repo = tmp_path / "repo"
    (repo / "var" / "gates").mkdir(parents=True)
    monkeypatch.setattr(gates, "REPO_ROOT", repo)
    missing = gates.check_scope("apply", "dev", repo_root=repo)
    assert missing == ["M-01", "M-02", "M-03", "M-09"]
    record = gates.build_record(
        gate="M-01",
        recorded_by="Luis",
        environment="dev",
        recorded_at="2026-09-01",
        deliverables={
            "aws_account_id": "123456789012",
            "credential_method": "oidc",
            "profile_or_role": "arn:aws:iam::123456789012:role/plan",
        },
    )
    output = gates.default_output("dev", "M-01", repo_root=repo)
    gates.write_record(record, output)
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["deliverables"]["aws_account_id"] == "123456789012"
    markdown = output.with_suffix(".md").read_text(encoding="utf-8")
    assert "AKIA" not in markdown
    assert "must not contain secrets" in markdown
    assert gates.main(["--list"]) == 0
    assert gates.main(["--print-checklist", "M-09"]) == 0
    env = {
        "AWS_ACCOUNT_ID": "123456789012",
        "AWS_REGION": "us-east-1",
        "PLAN_ROLE_ARN": "arn:aws:iam::123456789012:role/plan",
    }
    assert gates.check_scope("plan", "dev", repo_root=repo, from_env=True, environ=env) == []
    assert gates.main(["--check", "--scope", "local", "--environment", "local"]) == 0


def test_cli_review_apply_writes_record(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    gates = _load("record_gate")
    output = tmp_path / "m09.json"
    digest = "123.dkr.ecr.us-east-1.amazonaws.com/api@sha256:" + ("cd" * 32)
    assert (
        gates.main(
            [
                "--review-apply",
                "--environment",
                "dev",
                "--recorded-by",
                "Luis",
                "--account",
                "123456789012",
                "--role",
                "github-deploy-dev",
                "--region",
                "us-east-1",
                "--image-digest",
                digest,
                "--confirm",
                "1",
                "--output",
                str(output),
            ]
        )
        == 0
    )
    assert output.is_file()
    printed = capsys.readouterr().out
    assert str(output) in printed


def test_waivers_and_bedrock_requirement() -> None:
    gates = _load("record_gate")
    waived = gates.build_record(
        gate="M-04",
        recorded_by="Luis",
        environment="dev",
        status="waived",
        notes="stub provider until live eval",
    )
    assert waived["status"] == "waived"
    with pytest.raises(ValueError, match="cannot be waived"):
        gates.build_record(
            gate="M-01",
            recorded_by="Luis",
            environment="dev",
            status="waived",
            notes="no",
        )
    with pytest.raises(ValueError, match="production"):
        gates.build_record(
            gate="M-06",
            recorded_by="Luis",
            environment="prod",
            status="waived",
            notes="managed domain",
        )


def test_code_does_not_assume_gated_decisions() -> None:
    for folder in ("domain", "application"):
        offenders: list[str] = []
        for path in (API_SRC / folder).rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for name in COMMERCIAL_MODEL_NAMES:
                if name in text:
                    offenders.append(f"{path.relative_to(API_SRC)}:{name}")
        assert offenders == []
    config = (API_SRC / "config.py").read_text(encoding="utf-8")
    assert 'ai_provider: AiProvider = "stub"' in config
    assert 'bedrock_model_id: str = ""' in config
    identity = (
        REPO_ROOT / "infrastructure" / "terraform" / "modules" / "identity" / "variables.tf"
    ).read_text(encoding="utf-8")
    assert "Keep false until a user-policy review" in identity
    for environment in ("dev", "prod"):
        tfvars = (
            REPO_ROOT
            / "infrastructure"
            / "terraform"
            / "environments"
            / environment
            / "terraform.tfvars"
        ).read_text(encoding="utf-8")
        assert 'aws_account_id              = ""' in tfvars
        assert "allow_self_registration     = false" in tfvars
        assert 'bedrock_model_id            = ""' in tfvars
        assert 'ai_provider                 = "stub"' in tfvars
    bootstrap = (
        REPO_ROOT / "infrastructure" / "terraform" / "bootstrap" / "variables.tf"
    ).read_text(encoding="utf-8")
    assert "Empty disables allowed_account_ids until a human records the account" in bootstrap


def test_docs_never_ask_for_forbidden_plan_inputs() -> None:
    for path in (*DOCS.glob("*.md"), REPO_ROOT / "README.md"):
        text = path.read_text(encoding="utf-8")
        if path.name == "GATES.md":
            continue
        assert SECRET_REQUEST.search(text) is None, path.name
        assert "AWS_SECRET_ACCESS_KEY=" not in text
    contributing = (DOCS / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "GATES.md" in contributing


def test_workflows_print_apply_checklist_and_never_auto_approve_plan() -> None:
    plan = (WORKFLOWS / "terraform-plan.yml").read_text(encoding="utf-8")
    assert "record_gate.py" in plan
    assert "--print-checklist M-09" in plan
    assert "-auto-approve" not in plan
    for name in ("deploy-dev.yml", "deploy-prod.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "record_gate.py" in text
        assert "--print-checklist M-09" in text
        assert "apply -auto-approve" not in text
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    assert "record-gate" in makefile
    assert "check-gates" in makefile
    assert "review-apply" in makefile
