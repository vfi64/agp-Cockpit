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
    return ""
