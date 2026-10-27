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
    # AGP_CI_DEPS_RETRY_V1 (main run of #377): two bounded attempts per install, so a slow mirror
    # gets a second chance and a hanging one still ends red within the job limit.
    assert jobs["python"]["timeout-minutes"] <= 30 and jobs["browser"]["timeout-minutes"] <= 40
    steps = jobs["browser"]["steps"]
    installs = [step for step in steps if "playwright install" in str(step.get("run", ""))]
    assert len(installs) == 2 and all(step.get("timeout-minutes", 999) <= 16 for step in installs)
    for step in installs:
        assert "for attempt in 1 2" in step["run"] and "timeout 420 npx playwright install" in step["run"]
        assert step["run"].rstrip().endswith("exit 1")
    apt = next(i for i, step in enumerate(steps) if "Acquire::Retries" in str(step.get("run", "")))
    assert apt < steps.index(installs[0])


def test_runner_image_is_pinned_and_actions_run_on_node_24():
    # AGP_CI_RUNNER_PINNED_V1: checked against each action's action.yml ("using: node24").
    text = SOURCE.read_text(encoding="utf-8")
    assert "runs-on: ubuntu-latest" not in text and text.count("runs-on: ubuntu-24.04") == 3
    for action in ("actions/checkout@v5", "actions/setup-python@v6", "actions/setup-node@v5", "actions/cache@v5"):
        assert action in text, action
    assert not re.search(r"actions/(checkout|setup-node|cache)@v4|actions/setup-python@v5", text)



def test_refresh_pull_requests_take_the_kits_light_path_and_everything_else_runs_full():
    """AGP_CI_LIGHT_REFRESH_V1 (Kit 1.0.25, KIT-GF-063): `agentic-kit ci runtime-plan` decides; Kit check and
    doctor always run; a missing or failed classification is full."""
    jobs = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["jobs"]
    python, browser = jobs["python"], jobs["browser"]
    plan = next(step for step in python["steps"] if step.get("id") == "plan")
    assert plan["if"] == "github.event_name == 'pull_request'"                 # a push to main is full
    assert "agentic-kit ci runtime-plan" in plan["run"] and 'echo "mode=full"' in plan["run"]
    assert python["outputs"]["mode"] == "${{ steps.plan.outputs.mode }}"
    assert python["steps"][0].get("with", {}).get("fetch-depth") == 0             # base and head are local
    pytest_step = next(step for step in python["steps"] if "pytest" in str(step.get("run", "")))
    kit_step = next(step for step in python["steps"] if "agentic-kit check" in str(step.get("run", "")))
    assert pytest_step["if"] == "steps.plan.outputs.mode != 'light'" and "if" not in kit_step
    # AGP_CI_RUFF_V1 (2026-10-27): without ruff the CI skipped tests/test_lint_clean.py, and eight
    # findings on main surfaced only on the owner's Mac during the Kit 1.1.6 adoption.
    assert re.search(r'"ruff==\d+\.\d+\.\d+"', pytest_step["run"]), pytest_step["run"]
    # AGP_CI_LIGHT_SKIP_DECLARED_V1 (Kit 1.1.2, KIT-GF-073; replaces AGP_CI_LIGHT_NO_SKIP_V1): the browser job is
    # skipped on the light path only; a failed classification still runs it (always()). The gate accepts a skipped
    # browser job only together with the light verdict, and the workspace declares the check for the Kit.
    assert browser["needs"] == "python" and browser["if"] == "always() && needs.python.outputs.mode != 'light'"
    assert not any("outputs.mode" in str(step.get("if", "")) for step in browser["steps"])
    gate = jobs["agentic-gate"]["steps"][0]["run"]
    assert 'needs.browser.result }}" = "success" || {' in gate
    assert 'test "${{ needs.browser.result }}" = "skipped" && test "${{ needs.python.outputs.mode }}" = "light"' in gate
    config = yaml.safe_load((ROOT / ".agentic/config.yaml").read_text(encoding="utf-8"))
    assert config["gates"]["light_path_skipped_checks"] == ["browser"]
    text = SOURCE.read_text(encoding="utf-8")
    assert text.count("agentic-project-kit") == 1                              # kit update keeps one pin


def test_the_late_required_check_is_declared_for_the_kits_ci_wait():
    """AGP_CI_REQUIRED_CHECKS_DECLARED_V1 (Kit 1.1.4, KIT-GF-079): agentic-gate starts only after python and browser,
    so its check does not exist while they run; the Kit's CI wait must wait for it by name (main is not protected)."""
    jobs = yaml.safe_load(SOURCE.read_text(encoding="utf-8"))["jobs"]
    config = yaml.safe_load((ROOT / ".agentic/config.yaml").read_text(encoding="utf-8"))
    assert config["gates"]["required_checks"] == ["agentic-gate"]
    assert "name" not in jobs["agentic-gate"]                                   # the check is named after the job id
    assert jobs["agentic-gate"]["needs"] == ["python", "browser"] and jobs["browser"]["needs"] == "python"


def test_workspace_config_has_no_duplicate_keys():
    """A broken comment line once left `publication: github);` beside `publication: github` (YAML kept the last)."""
    class Strict(yaml.SafeLoader):
        pass

    def mapping(loader, node, deep=False):
        keys = [loader.construct_object(key, deep=deep) for key, _ in node.value]
        duplicates = sorted({key for key in keys if keys.count(key) > 1})
        assert not duplicates, f"duplicate keys {duplicates} at line {node.start_mark.line + 1}"
        return yaml.SafeLoader.construct_mapping(loader, node, deep)

    Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    for path in (ROOT / ".agentic/config.yaml", SOURCE):
        yaml.load(path.read_text(encoding="utf-8"), Loader=Strict)
