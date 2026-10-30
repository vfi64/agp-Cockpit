"""AGP_RECOVER_MAIN_BEHIND_V1 (live 2026-10-29, Kit repository): main was only behind origin/main.
„Wiederherstellen“ ran without network, diagnosed against the stale local origin/main ref, found main
"synchronized" and asked for an unrelated decision. The Lage now names the case, and the recover task
carries the live facts and approves exactly the Kit's fast-forward of main."""
from __future__ import annotations

import os
import subprocess

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core import standard_tasks as st

A, B = "a" * 40, "b" * 40
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "PATH": os.environ.get("PATH", "/usr/bin:/bin")}


def facts(**kw):
    base = {"root": "/r", "is_git": True, "branch": "main", "head": A, "origin_main": B, "tracking_main": A,
            "own_commits": 0, "kit_version": "1.1.8", "workspace": True, "gh_ok": True, "post_merge": "PASS"}
    base.update(kw)
    return rs.RepoFacts(**base)


def test_main_only_behind_is_named_in_the_lage():
    state = rs.classify(facts())
    assert state.state == rs.STOERUNG and state.recommended == rs.WIEDERHERSTELLEN
    assert any("nur hinter origin/main" in reason for reason in state.reasons)


def test_other_drift_is_not_called_only_behind():
    for kw in ({"own_commits": 2}, {"changes": ("x.py",)}, {"branch": "feat/x"}, {"origin_main": A},
               {"own_commits": None}):
        assert not rs.main_only_behind(facts(**kw)), kw
    state = rs.classify(facts(own_commits=1))
    assert not any("nur hinter origin/main" in reason for reason in state.reasons)


def _git(root, *args):
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, env=ENV, check=False)
    assert done.returncode == 0, done.stderr
    return done.stdout.strip()


def _behind_checkout(tmp_path):
    origin, work = tmp_path / "origin.git", tmp_path / "work"
    _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    _git(tmp_path, "clone", "-q", str(origin), str(work))
    for n in (1, 2):
        (work / "f.txt").write_text(f"{n}\n")
        _git(work, "add", ".")
        _git(work, "commit", "-qm", f"c{n}")
    _git(work, "push", "-q", "origin", "HEAD:main")
    _git(work, "reset", "-q", "--hard", "HEAD~1")
    _git(work, "update-ref", "refs/remotes/origin/main", "HEAD")    # stale tracking ref, as on the Mac
    return work


def test_the_recover_task_approves_only_the_fast_forward_when_main_is_behind(tmp_path, monkeypatch):
    work = _behind_checkout(tmp_path)
    monkeypatch.chdir(work)
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    task = st.BY_KEY["recover"]
    assert task.scope(work) == st.RECOVER_SYNC_SCOPE
    assert st.RECOVER_SYNC_SCOPE == {"agentic-kit transfer fetch-origin", "agentic-kit transfer sync-main",
                                     "agentic-kit transfer pull-current"}
    prompt = task.prompt(work)
    assert "Observed by the Cockpit before the start" in prompt and "stale" in prompt
    assert _git(work, "rev-parse", "HEAD") in prompt


def test_the_recover_task_keeps_asking_for_everything_otherwise(tmp_path, monkeypatch):
    work = _behind_checkout(tmp_path)
    (work / "dirty.txt").write_text("x\n")
    monkeypatch.chdir(work)
    task = st.BY_KEY["recover"]
    assert task.scope(work) is None
    assert "Observed by the Cockpit before the start" not in task.prompt(work)
    (work / "dirty.txt").unlink()
    _git(work, "pull", "-q", "--ff-only", "origin", "main")       # synchronized: nothing to approve
    assert task.scope(work) is None
