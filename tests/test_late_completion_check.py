"""AGP_LATE_COMPLETION_CHECK_V1 (live 2026-10-04, step 1689): after an assistant
timeout the Cockpit confirms a finished „Abschließen“ from the repository itself."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from agp_cockpit.core import repo_state as rs
from agp_cockpit.core.standard_task_progress import (
    late_completion_verdict,
    stopped_by_assistant_timeout,
)

TIMEOUT = ("K07_ASSISTANT_RESPONSE_TIMEOUT after 181s (180s without visible activity) — "
           "Mensch muss prüfen: keine Datei 1689_*.py oder 1689_agp_terminal.json erschienen")


def git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          cwd=repo, text=True, capture_output=True, check=True)
    return done.stdout.strip()


def commit(repo: Path, name: str, text: str, message: str) -> str:
    (repo / name).write_text(text)
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def repo(tmp_path):
    """main A; feat B (the started work); origin/main at A."""
    git(tmp_path, "init", "-q", "-b", "main")
    a = commit(tmp_path, "base.txt", "a\n", "A")
    git(tmp_path, "update-ref", "refs/remotes/origin/main", a)
    git(tmp_path, "switch", "-q", "-c", "feat")
    commit(tmp_path, "feature.txt", "f\n", "B")
    return tmp_path


def state(name=rs.BEREIT, post_merge="PASS"):
    return SimpleNamespace(state=name, summary="s", facts=SimpleNamespace(post_merge=post_merge))


def squash_merge(repo: Path) -> None:
    git(repo, "switch", "-q", "main")
    commit(repo, "feature.txt", "f\n", "Squash feat (#196)")
    git(repo, "update-ref", "refs/remotes/origin/main", "main")
    git(repo, "branch", "-q", "-D", "feat")   # the Kit deletes the merged branch


def test_only_an_assistant_timeout_triggers_the_check():
    assert stopped_by_assistant_timeout({"state": "STOPPED", "last_summary": TIMEOUT})
    assert stopped_by_assistant_timeout({"state": "STOPPED", "last_error": TIMEOUT})
    assert not stopped_by_assistant_timeout({"state": "STOPPED", "last_summary": "Stopped by user"})
    assert not stopped_by_assistant_timeout({"state": "NEEDS_HUMAN", "last_summary": TIMEOUT})
    assert not stopped_by_assistant_timeout(None)


def test_merged_work_with_green_post_merge_is_confirmed(repo):
    start = git(repo, "rev-parse", "HEAD")
    squash_merge(repo)
    done, text = late_completion_verdict("finish", start, state(), repo)
    assert done, text
    assert "abgeschlossen; nur die Abschlussmeldung" in text and start[:12] in text


def test_unmerged_work_or_red_post_merge_is_not_confirmed(repo):
    start = git(repo, "rev-parse", "HEAD")
    git(repo, "switch", "-q", "main")   # e.g. remote-next switched to main without merging
    done, text = late_completion_verdict("finish", start, state(), repo)
    assert not done and "has changes not in origin/main" in text
    squash_merge(repo)
    done, text = late_completion_verdict("finish", start, state(post_merge="NOT_PASS"), repo)
    assert not done and "post-merge-check NOT_PASS" in text
    done, text = late_completion_verdict("finish", start, state(rs.STOERUNG), repo)
    assert not done and f"Lage {rs.STOERUNG}" in text


def test_other_tasks_only_report_the_lage(repo):
    done, text = late_completion_verdict("work-start", "", state(rs.IN_ARBEIT), repo)
    assert not done and f"Lage {rs.IN_ARBEIT}" in text
