"""P10a Pflege (AGP_MAINTENANCE_VERIFIER_V1, AGP_OWNER_DECISION_EXECUTE_V1,
AGP_CI_UPDATE_GUARD_V1; owner 2026-10-04)."""

import subprocess
from pathlib import Path

import pytest

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core import standard_verifier as sv
from agp_cockpit.core.command_file_contract import validate_command_content
from agp_cockpit.core.kit_command_catalog import (
    KitCommandCatalog,
    approval_required_commands,
    forbidden_execute_violations,
)
from agp_cockpit.core.standard_tasks import BY_KEY, WORK_START_SCOPE, maintenance_branch
from agp_cockpit.core.verbs import BY_KEY as VERBS

ROOT = Path(__file__).resolve().parents[1]
TASK = BY_KEY["maintain"]


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=repo, text=True, capture_output=True, check=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    (root / "a.txt").write_text("a\n")
    git(root, "add", "a.txt")
    git(root, "commit", "-q", "-m", "a")
    git(root, "update-ref", "refs/remotes/origin/main", "main")
    return root


def work_order(*argv: str) -> str:
    return ("import subprocess\n"
            f"ARGV = {list(argv)!r}\n"
            "def main():\n    subprocess.run(ARGV)\n")


def test_pflege_is_a_standard_task_with_only_the_work_start_scope():
    assert VERBS[rs.PFLEGE].task_key == "maintain" and VERBS[rs.PFLEGE].slice is None
    assert TASK.approved_scope == WORK_START_SCOPE and not TASK.ci_gate_merge and TASK.confirm
    assert TASK.contract(ROOT)["completion_contract"]["verifier"] == "maintained"


def test_precheck_needs_a_clean_synchronized_main_and_one_branch_per_day(repo):
    assert TASK.check(repo) is None
    (repo / "x.txt").write_text("x")
    assert "ungesicherte" in TASK.check(repo)
    (repo / "x.txt").unlink()
    git(repo, "branch", maintenance_branch())
    assert "existiert schon" in TASK.check(repo)
    git(repo, "branch", "-D", maintenance_branch())
    git(repo, "switch", "-q", "-c", "feat/x")
    assert "nur auf main" in TASK.check(repo)


def test_verifier_accepts_nothing_on_main_or_changes_on_the_branch(repo):
    branch = maintenance_branch("2026-10-04")
    assert sv.verify_maintained(repo, branch=branch)[0]                     # nothing to maintain
    (repo / "dirty.txt").write_text("x")
    ok, why = sv.verify_maintained(repo, branch=branch)
    assert not ok and "uncommitted" in why
    (repo / "dirty.txt").unlink()
    git(repo, "switch", "-q", "-c", branch)
    ok, why = sv.verify_maintained(repo, branch=branch)
    assert not ok and "no changes" in why                                    # an empty branch is wrong
    (repo / ".agentic").mkdir()
    (repo / ".agentic/config.yaml").write_text("schema: 2\n")
    assert sv.verify_maintained(repo, branch=branch)[0]                     # uncommitted changes count
    git(repo, "switch", "-q", "-c", "feat/other")
    assert "expected main or" in sv.verify_maintained(repo, branch=branch)[1]


def test_prompt_names_no_kit_command_and_keeps_the_sweep_a_report():
    prompt = TASK.prompt(ROOT)
    for command in ("artifact-gc", "workspace upgrade", "docs lifecycle sweep", "ci-update", "work start"):
        assert command not in prompt
    assert "command digest" in prompt and "Never execute the sweep" in prompt and "KIT-GF-042" in prompt


def test_sweep_execute_asks_and_its_dry_run_is_free():
    catalog = KitCommandCatalog.load(ROOT)
    assert approval_required_commands(work_order("agentic-kit", "docs", "lifecycle", "sweep", "--dry-run",
                                                 "--json"), catalog) == []
    assert approval_required_commands(work_order("agentic-kit", "docs", "lifecycle", "sweep", "--execute",
                                                 "--only", "x"), catalog) == \
        ["agentic-kit docs lifecycle sweep --execute"]
    assert approval_required_commands(work_order("agentic-kit", "artifact-gc", "--transfer-runs",
                                                 "--execute"), catalog) == []


def test_ci_update_execute_is_rejected_and_its_dry_run_allowed():
    assert forbidden_execute_violations(work_order("agentic-kit", "workspace", "ci-update", "--json")) == []
    found = forbidden_execute_violations(work_order("agentic-kit", "workspace", "ci-update", "--execute"))
    assert len(found) == 1 and "KIT-GF-042" in found[0]
    hidden = ("import subprocess, sys\nFLAG = '--execute'\n"
              "def main():\n    subprocess.run(['agentic-kit', 'workspace', 'ci-update', FLAG])\n")
    assert forbidden_execute_violations(hidden)
    with pytest.raises(ValueError, match="KIT-GF-042"):
        validate_command_content(work_order("agentic-kit", "workspace", "ci-update", "--execute"),
                                 filename="1800_x.py", repository_root=ROOT)
