"""T4 (live 2026-10-02, steps 1573/1574): no second pull request for a merged
branch, Cockpit-verified facts in every continuation, Kit verdict rule."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import bridge_server
from agp_cockpit.core import merged_branch_guard as g
from agp_cockpit.core.command_file_contract import (
    WORK_ORDER_KIT_RULE,
    validate_command_content,
)

ROOT = Path(__file__).resolve().parents[1]


def git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=repo, text=True, capture_output=True, check=True)
    return completed.stdout.strip()


def commit(repo: Path, name: str, text: str, message: str) -> str:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    """main A; feat adds feature.txt; origin/main still at A."""
    git(tmp_path, "init", "-q", "-b", "main")
    a = commit(tmp_path, "base.txt", "a\n", "A")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", a)
    git(tmp_path, "switch", "-q", "-c", "feat")
    commit(tmp_path, "feature.txt", "f\n", "B")
    git(tmp_path, "update-ref", "refs/remotes/origin/feat", "feat")
    git(tmp_path, "switch", "-q", "main")
    return tmp_path


def squash_merge(repo: Path) -> None:
    """What GitHub's squash merge plus the Kit's successor refresh produce."""
    commit(repo, "feature.txt", "f\n", "Squash feat (#147)")
    commit(repo, ".agentic-refresh.txt", "r\n", "Refresh successor package (#148)")
    git(repo, "update-ref", "refs/remotes/origin/main", "main")


def work_order(head: str | None = "feat") -> str:
    head_args = f'"--head", "{head}", ' if head else ""
    return (
        "import sys\nfrom pathlib import Path\nSTEP = 1574\n"
        "def main():\n"
        '    if "--self-test" in sys.argv:\n        return 0\n'
        f'    argv = ["agentic-kit", "transfer", "pr-create-complete", "--title", "t", {head_args}'
        '"--base", "main", "--post-merge-complete", "--json"]\n'
        '    Path("Download/1574_x_return_bundle.json").write_text("{}")\n'
        'if __name__ == "__main__":\n    main()\n'
    )


def test_relation_follows_the_squash_merge(repo):
    assert g.relation(repo, "feat") == g.CHANGES
    assert g.violations(work_order(), repo) == []
    squash_merge(repo)
    assert g.relation(repo, "feat") == g.MERGED
    assert "already in origin/main" in g.violations(work_order(), repo)[0]


def test_deleted_local_branch_falls_back_to_the_remote_tracking_ref(repo):
    squash_merge(repo)
    git(repo, "branch", "-q", "-D", "feat")
    assert g.resolve(repo, "feat") == "origin/feat"
    assert g.violations(work_order(), repo)


def test_current_branch_is_used_without_head_and_a_dirty_tree_is_not_blocked(repo):
    squash_merge(repo)
    git(repo, "switch", "-q", "feat")
    assert g.violations(work_order(head=None), repo)
    (repo / "new.txt").write_text("n\n")
    assert g.violations(work_order(head=None), repo) == []


def test_branch_without_own_commits_and_unknown_refs_are_not_blocked(repo, tmp_path_factory):
    git(repo, "switch", "-q", "-c", "fresh")
    assert g.relation(repo, "fresh") == g.NO_COMMITS
    assert g.violations(work_order("fresh"), repo) == []
    assert g.relation(repo, "missing") is None
    plain = tmp_path_factory.mktemp("plain")
    assert g.violations(work_order(), plain) == []
    assert g.repository_facts(plain) is None


def test_the_violation_is_a_correctable_contract_rejection(repo):
    squash_merge(repo)
    with pytest.raises(ValueError) as caught:
        validate_command_content(work_order(), filename="1574_x.py", repository_root=repo,
                                 allow_remote_effects=True)
    assert "AGP_MERGED_BRANCH_GUARD_V1" in str(caught.value)
    assert bridge_server._correctable(caught.value)


def test_facts_name_the_merged_branch_and_forbid_rechecks(repo):
    squash_merge(repo)
    line = g.repository_facts(repo, work_order())
    assert "current branch main" in line and "main equals origin/main: yes" in line
    assert "feat adds nothing to origin/main (already merged)" in line
    assert "never re-run a remote-effect command" in line


def test_pull_requests_are_listed_when_gh_is_available(repo):
    def runner(argv, **_):
        if argv[0] == "gh":
            return SimpleNamespace(returncode=0, stdout=json.dumps(
                [{"number": 149, "state": "OPEN"}, {"number": 147, "state": "MERGED"}]), stderr="")
        raise AssertionError(argv)
    assert g._pull_requests(repo, "feat", "gh", runner) == "#149 OPEN, #147 MERGED"
    assert g._pull_requests(repo, "feat", None, runner) is None


def test_continuation_carries_the_facts(repo):
    from agp_cockpit.core.file_loop_orchestrator import _with_next_local_step
    squash_merge(repo)
    (repo / "Download").mkdir()
    order = repo / "Download" / "1574_x.py"
    order.write_text(work_order())
    text = _with_next_local_step("Result.\n", repo, 1574, command_file=order)
    assert "Cockpit-verified repository facts (local git):" in text
    assert "feat adds nothing to origin/main (already merged)" in text


def test_the_rule_asks_for_the_kit_verdict_and_forbids_rechecks():
    for part in ("result_status", "final_signal", "failed_step", "next_action",
                 "Never re-run a command with remote effects"):
        assert part in WORK_ORDER_KIT_RULE
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    assert WORK_ORDER_KIT_RULE in content


def test_live_1574_would_have_been_stopped():
    """The real step-1574 order against the real refs of that moment, if the
    repository still has them (developer checkout, not CI)."""
    order = ROOT / "Download" / "1574_agp_pr_create_complete_recheck.py"
    if not order.is_file():
        pytest.skip("live evidence not present")
    ok = subprocess.run(["git", "cat-file", "-e", "5c1544c^{commit}"], cwd=ROOT,
                        capture_output=True, check=False).returncode == 0
    if not ok:
        pytest.skip("commit 5c1544c not present")
    assert g.relation(ROOT, "639d895", "5c1544c") == g.MERGED
    assert g.relation(ROOT, "639d895", "effbc85") == g.CHANGES
