"""AGP_WORK_BRANCH_BEHIND_V1 (live 2026-10-27 and 2026-10-30): origin/<branch> had commits pushed from
elsewhere; the Lage still offered the stale local work branch for „Arbeiten“ and „Abschließen“. The
Lage now names the case, both start paths refuse it, and „Wiederherstellen“ carries the live facts and
approves exactly the Kit's fetch and fast-forward of the branch."""
from __future__ import annotations

import os
import subprocess

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core import standard_tasks as st
from agp_cockpit.core.work_tab_guard import behind_origin_reason, work_task_block_reason

A, B = "a" * 40, "b" * 40
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "PATH": os.environ.get("PATH", "/usr/bin:/bin")}
BRANCH = "fix/demo"


def facts(**kw):
    base = {"root": "/r", "is_git": True, "branch": BRANCH, "head": A, "origin_main": B, "tracking_main": B,
            "own_commits": 1, "kit_version": "1.1.8", "workspace": True, "gh_ok": True,
            "branch_published": True, "published_head": A, "published_remote": B, "branch_relation": rs.BEHIND}
    base.update(kw)
    return rs.RepoFacts(**base)


def test_a_clean_branch_behind_its_origin_is_a_stoerung_with_wiederherstellen():
    for relation in (rs.BEHIND, rs.NOT_FETCHED):
        state = rs.classify(facts(branch_relation=relation))
        assert state.state == rs.STOERUNG and state.recommended == rs.WIEDERHERSTELLEN, rs.describe(state)
        assert rs.ARBEITEN not in state.offered and rs.ABSCHLIESSEN not in state.offered
        assert any("Fast-Forward" in reason for reason in state.reasons)
        assert rs.work_branch_only_behind(facts(branch_relation=relation))


def test_diverged_or_dirty_is_named_but_not_called_only_behind():
    diverged = rs.classify(facts(branch_relation=rs.DIVERGED))
    assert diverged.state == rs.STOERUNG and any("auseinandergelaufen" in r for r in diverged.reasons)
    assert not rs.work_branch_only_behind(facts(branch_relation=rs.DIVERGED))
    dirty = facts(changes=("src/x.py",))
    assert not rs.work_branch_only_behind(dirty)
    assert any("Offene Änderungen" in r for r in rs.classify(dirty).reasons)


def test_ahead_same_unpublished_and_transfer_branches_are_unchanged():
    for kw in ({"branch_relation": rs.AHEAD}, {"branch_relation": rs.SAME}, {"branch_relation": ""},
               {"branch": "transfer/x", "branch_relation": rs.BEHIND}):
        state = rs.classify(facts(**kw))
        assert state.state == rs.IN_ARBEIT, (kw, rs.describe(state))


def _git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=ENV, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _commit(work, n):
    (work / "f.txt").write_text(f"{n}\n")
    _git(work, "add", ".")
    _git(work, "commit", "-qm", f"c{n}")


def _checkout_behind(tmp_path, *, fetched: bool):
    """A work branch whose origin/<branch> got a commit from another clone."""
    origin, work, other = tmp_path / "origin.git", tmp_path / "work", tmp_path / "other"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    _commit(work, 0)
    _git(work, "push", "-q", "origin", "HEAD:main")
    _git(work, "switch", "-qc", BRANCH)
    _commit(work, 1)
    _git(work, "push", "-q", "-u", "origin", BRANCH)
    _git(tmp_path, "clone", "-q", "-b", BRANCH, str(origin), str(other))
    _commit(other, 2)
    _git(other, "push", "-q", "origin", BRANCH)
    if fetched:
        _git(work, "fetch", "-q", "origin")
    return work, _git(other, "rev-parse", "HEAD")


def test_observe_reads_the_relation_live_from_github(tmp_path):
    work, remote = _checkout_behind(tmp_path, fetched=False)
    observed = rs.observe(work, kit=None, network=True)
    assert observed.published_remote == remote and observed.branch_relation == rs.NOT_FETCHED
    offline = rs.observe(work, kit=None, network=False)     # only the stale tracking ref
    assert offline.branch_relation == rs.SAME
    _git(work, "fetch", "-q", "origin")
    assert rs.observe(work, kit=None, network=True).branch_relation == rs.BEHIND
    _git(work, "pull", "-q", "--ff-only")
    assert rs.observe(work, kit=None, network=True).branch_relation == rs.SAME
    _commit(work, 3)
    assert rs.observe(work, kit=None, network=True).branch_relation == rs.AHEAD


def test_both_start_paths_refuse_a_branch_behind_its_origin(tmp_path):
    work, _remote = _checkout_behind(tmp_path, fetched=False)
    reason = work_task_block_reason(work)
    assert reason.startswith("Blockiert — fix/demo ist hinter origin/fix/demo") and "Wiederherstellen" in reason
    finish = st._finish_precheck(work, {})
    assert finish and "dann Abschließen" in finish
    _git(work, "pull", "-q", "--ff-only")
    assert behind_origin_reason(work, BRANCH) == "" and work_task_block_reason(work) == ""


def test_a_branch_github_cannot_tell_about_is_not_refused(tmp_path):
    work, _remote = _checkout_behind(tmp_path, fetched=True)
    _git(work, "remote", "set-url", "origin", str(tmp_path / "missing.git"))
    assert behind_origin_reason(work, BRANCH) == ""


def test_the_recover_task_approves_only_fetch_and_fast_forward_for_the_branch(tmp_path):
    work, remote = _checkout_behind(tmp_path, fetched=False)
    task = st.BY_KEY["recover"]
    assert task.scope(work) == st.RECOVER_SYNC_SCOPE
    prompt = task.prompt(work)
    assert "work branch only behind origin/fix/demo" in prompt and remote in prompt
    assert "is not fetched yet" in prompt and "never a merge, rebase, reset or discard" in prompt
    (work / "f.txt").write_text("dirty\n")
    assert task.scope(work) is None
    assert "work branch only behind" not in task.prompt(work)
