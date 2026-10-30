"""AGP_WORK_TASK_NOT_ON_MAIN_V1: an „Arbeiten“ task starts only on a work branch.

Live 2026-10-26 (Kit repository, steps 91–93): the owner started an „Arbeiten“ task without
„Arbeit beginnen“. The task ran on main, failed its own branch check three times and used up the
error budget of the mission. Work happens on a work branch the Kit started; „Arbeit beginnen“
(Standard Tasks) starts one. The start path refuses main, master and a detached HEAD.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

MAIN_BRANCHES = frozenset({"main", "master"})


def current_branch(root: Path, *, runner=subprocess.run) -> str | None:
    """The checked-out branch; "" for a detached HEAD; None when git cannot tell."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    try:
        done = runner(["git", "branch", "--show-current"], cwd=str(root), env=env, text=True,
                      capture_output=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if getattr(done, "returncode", 1) != 0:
        return None
    return str(getattr(done, "stdout", "") or "").strip()


def work_task_block_reason(root: Path, *, runner=subprocess.run) -> str:
    """Why an „Arbeiten“ task may not start here ("" when it may)."""
    branch = current_branch(root, runner=runner)
    if branch is None:
        return ""                     # not a git checkout the Cockpit can read: no evidence to refuse
    if branch == "":
        return ("Blockiert — kein Branch ausgecheckt (detached HEAD). Erst unter „Standard Tasks“ "
                "„Arbeit beginnen“, dann hier starten.")
    if branch in MAIN_BRANCHES:
        return (f"Blockiert — das Repository steht auf {branch}. Ein Auftrag im Tab „Arbeiten“ läuft "
                "auf einem Arbeitsbranch: erst unter „Standard Tasks“ „Arbeit beginnen“, dann hier "
                "starten.")
    return behind_origin_reason(root, branch, runner=runner)


def behind_origin_reason(root: Path, branch: str, *, runner=subprocess.run) -> str:
    """AGP_WORK_BRANCH_BEHIND_V1: why work may not continue on ``branch`` because origin/<branch> on
    GitHub has commits that are missing locally ("" when it may, or when GitHub cannot be read).
    Transfer branches belong to the Kit's FILE_TRANSFER and are never judged here."""
    from agp_cockpit.core import repo_state as rs
    if not branch or branch in MAIN_BRANCHES or branch.startswith(rs.TRANSFER_BRANCH_PREFIX):
        return ""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")

    def git(*args: str):
        try:
            return runner(["git", *args], cwd=str(root), env=env, text=True, capture_output=True,
                          timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return None

    head = git("rev-parse", "HEAD")
    remote = git("ls-remote", "origin", f"refs/heads/{branch}")
    if head is None or remote is None or head.returncode != 0 or remote.returncode != 0:
        return ""
    words = str(remote.stdout or "").split()
    published = words[0] if words else ""
    relation = rs.branch_relation(root, str(head.stdout or "").strip(), published, runner=runner)
    if relation not in (rs.BEHIND, rs.NOT_FETCHED, rs.DIVERGED):
        return ""
    how = "auseinandergelaufen mit" if relation == rs.DIVERGED else "hinter"
    return (f"Blockiert — {branch} ist {how} origin/{branch} auf GitHub (Commits von anderswo). Erst unter "
            "„Standard Tasks“ „Wiederherstellen“, dann weiterarbeiten.")
