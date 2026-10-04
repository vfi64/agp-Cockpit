"""AGP_FINISH_OPEN_FOLLOWUP_V1 and AGP_RECOVER_OFFER_CLEARS_V1 (live 2026-10-03/04).

#185: PR #184 was merged, main clean and synchronized, but the Kit's follow-up
pull request was still open (post-merge-check NOT_PASS). Abschließen refused
main, Wiederherstellen would only have reported the open pull request; the
lifecycle could be completed only through the decision box. Now Abschließen is
offered and recommended on clean, synchronized main whose only problem is the
open Kit post-merge lifecycle, and it runs a closeout-only prompt.

After that run the Lage still recommended „Wiederherstellen (nach dem letzten
Task)“ in BEREIT: the R6 offer of the interrupted Abschließen was never cleared.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core import standard_tasks as st

MAIN = "a" * 40


def _facts(**kw):
    base = {"root": "/r", "is_git": True, "branch": "main", "head": MAIN, "origin_main": MAIN,
            "tracking_main": MAIN, "own_commits": 0, "kit_version": "1.0.15", "workspace": True,
            "gh_ok": True, "post_merge": "NOT_PASS"}
    base.update(kw)
    return rs.RepoFacts(**base)


def test_open_followup_on_clean_main_offers_and_recommends_finish():
    state = rs.classify(_facts())
    assert state.state == rs.STOERUNG and state.recommended == rs.ABSCHLIESSEN
    assert rs.ABSCHLIESSEN in state.offered and rs.WIEDERHERSTELLEN in state.offered
    assert "Post-Merge-Abschluss" in state.summary


@pytest.mark.parametrize("kw", [{"head": "b" * 40}, {"changes": ("src/x.py",)}])
def test_other_main_problems_keep_wiederherstellen(kw):
    state = rs.classify(_facts(**kw))
    assert state.recommended == rs.WIEDERHERSTELLEN and rs.ABSCHLIESSEN not in state.offered


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   cwd=repo, check=True, capture_output=True)


@pytest.fixture
def main_repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / ".agentic").mkdir()
    (root / ".agentic/config.yaml").write_text("kit_schema_version: 2\n")
    _git(root, "add", ".")
    _git(root, "commit", "-q", "-m", "init")
    _git(root, "update-ref", "refs/remotes/origin/main", "main")
    return root


def _kit(monkeypatch, result):
    import agp_cockpit.core.kit_installation as ki
    monkeypatch.setattr(ki, "discover", lambda root: SimpleNamespace(binary=Path("/kit"), version="1.0.15"))
    monkeypatch.setattr(rs, "post_merge_check", lambda root, kit, **_kw: (result, ""))


def test_finish_precheck_allows_main_only_with_an_open_kit_lifecycle(main_repo, monkeypatch):
    finish = st.BY_KEY["finish"]
    _kit(monkeypatch, "NOT_PASS")
    assert finish.check(main_repo) is None
    _kit(monkeypatch, "PASS")
    assert "nie von main" in finish.check(main_repo)


def test_finish_precheck_refuses_dirty_or_unsynchronized_main(main_repo, monkeypatch):
    finish = st.BY_KEY["finish"]
    _kit(monkeypatch, "NOT_PASS")
    (main_repo / "wip.txt").write_text("w\n")
    assert "nie von main" in finish.check(main_repo)
    (main_repo / "wip.txt").unlink()
    _git(main_repo, "commit", "-q", "--allow-empty", "-m", "local")
    assert "nie von main" in finish.check(main_repo)


def test_finish_precheck_on_main_without_workspace_never_runs_the_kit(tmp_path, monkeypatch):
    root = tmp_path / "plain"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "commit", "-q", "--allow-empty", "-m", "init")
    _git(root, "update-ref", "refs/remotes/origin/main", "main")
    monkeypatch.setattr(rs, "post_merge_check", lambda *a, **k: pytest.fail("Kit must not run"))
    assert "nie von main" in st.BY_KEY["finish"].check(root)


def test_finish_prompt_on_main_is_closeout_only(main_repo):
    prompt = st.BY_KEY["finish"].prompt(main_repo)
    assert "complete the open post-merge lifecycle on main" in prompt
    assert "AGP_FINISH_OPEN_FOLLOWUP_V1" in prompt
    assert "do not open a" in prompt and "pull request for main" in prompt
    assert "pr-closeout-complete" in prompt


def test_finish_prompt_on_a_work_branch_is_unchanged(main_repo):
    _git(main_repo, "switch", "-q", "-c", "feat/x")
    prompt = st.BY_KEY["finish"].prompt(main_repo)
    assert prompt.startswith("STANDARD TASK — ABSCHLIESSEN (finish the work branch)")
