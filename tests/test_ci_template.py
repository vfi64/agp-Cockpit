"""AGP_CI_GATE_V2: invariants of the Kit-managed CI template."""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / ".agentic/ci/agentic-gate.yaml"
TARGET = ROOT / ".github/workflows/agentic-gate.yaml"
HEADER = "# managed template — source of truth: .agentic/ci/agentic-gate.yaml\n"


def test_workflow_is_the_managed_template_with_its_header():
    assert TARGET.read_text(encoding="utf-8") == HEADER + SOURCE.read_text(encoding="utf-8")


def test_push_runs_only_on_main_and_pr_runs_cancel_their_predecessor():
    flow = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))
    assert flow["on"]["push"] == {"branches": ["main"]}
    assert "pull_request" in flow["on"]
    assert "pull_request" in flow["concurrency"]["cancel-in-progress"]
    assert "github.sha" in flow["concurrency"]["group"]          # main runs never share a group


def test_kit_version_is_pinned():
    text = SOURCE.read_text(encoding="utf-8")
    assert re.search(r'agentic-project-kit==\d+\.\d+\.\d+', text)
    assert "pip install agentic-project-kit\n" not in text


def test_required_check_keeps_its_name_and_needs_both_jobs():
    jobs = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["jobs"]
    gate = jobs["agentic-gate"]
    assert gate["needs"] == ["python", "browser"] and gate["if"] == "always()"
    script = gate["steps"][0]["run"]
    assert 'needs.python.result }}" = "success"' in script and 'needs.browser.result }}" = "success"' in script
    python_steps = " ".join(str(s.get("run", "")) for s in jobs["python"]["steps"])
    assert "pytest" in python_steps and "agentic-kit check" in python_steps and "agentic-kit doctor" in python_steps
    assert any("playwright test" in str(s.get("run", "")) for s in jobs["browser"]["steps"])


def test_no_job_or_install_step_can_hang_for_hours():
    # AGP_CI_TIMEOUTS_V1 (live 2026-10-07: apt hung 23 min in install-deps on main).
    jobs = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["jobs"]
    assert jobs["python"]["timeout-minutes"] <= 30 and jobs["browser"]["timeout-minutes"] <= 30
    steps = jobs["browser"]["steps"]
    installs = [step for step in steps if "playwright install" in str(step.get("run", ""))]
    assert len(installs) == 2 and all(step.get("timeout-minutes", 999) <= 10 for step in installs)
    apt = next(i for i, step in enumerate(steps) if "Acquire::Retries" in str(step.get("run", "")))
    assert apt < steps.index(installs[0])

