"""Switch the local branch through the Kit (AGP_BRANCH_SWITCH_V1, owner 2026-10-07).

The owner switched every handed-over branch with ``git switch`` in the terminal.
The Kit has the route ``agentic-kit transfer branch-switch <branch>`` (remote
effects: none, without ``--pull``); the Cockpit offers it for local branches only,
never while a task runs (R5) and never over uncommitted changes. A branch with a
different build afterwards shows the stale-app line with „Neu bauen und neu starten“.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LocalBranch:
    name: str
    date: str
    subject: str
    current: bool


def _git(root: Path, runner, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    try:
        return runner(["git", *args], cwd=str(root), env=env, text=True, capture_output=True,
                      timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(args, 127, "", f"{type(exc).__name__}: {exc}")


def local_branches(root: Path, *, runner=subprocess.run) -> list[LocalBranch]:
    """Local branches, newest commit first."""
    current = _git(root, runner, "branch", "--show-current").stdout.strip()
    listed = _git(root, runner, "for-each-ref", "--sort=-committerdate",
                  "--format=%(refname:short)%09%(committerdate:short)%09%(subject)", "refs/heads")
    branches = []
    for line in listed.stdout.splitlines():
        name, _, rest = line.partition("\t")
        date, _, subject = rest.partition("\t")
        if name:
            branches.append(LocalBranch(name, date, subject, name == current))
    return branches


def block_reason(root: Path, branch: str, *, task_running: bool, runner=subprocess.run) -> str:
    """Why the switch is not allowed now ("" when it is)."""
    if task_running:
        return "Es läuft ein Task — Branch wechseln erst nach seinem Ende (R5)."
    names = {entry.name: entry for entry in local_branches(root, runner=runner)}
    if branch not in names:
        return f"„{branch}“ ist kein lokaler Branch."
    if names[branch].current:
        return f"„{branch}“ ist schon aktiv."
    dirty = [line for line in _git(root, runner, "status", "--porcelain").stdout.splitlines() if line.strip()]
    if dirty:
        return (f"{len(dirty)} nicht committete Änderung(en) — erst committen oder verwerfen; "
                "das Cockpit wechselt nie über offene Arbeit hinweg.")
    return ""


def switch(root: Path, kit_binary: Path, branch: str, *, runner=subprocess.run,
           env: dict | None = None) -> tuple[bool, str]:
    """Run the Kit route and verify the result with git (True, message)."""
    try:
        done = runner([str(kit_binary), "transfer", "branch-switch", branch, "--json"], cwd=str(root),
                      env=env, text=True, capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Kit nicht ausführbar: {exc}"
    current = _git(root, runner, "branch", "--show-current").stdout.strip()
    if done.returncode != 0 or current != branch:
        detail = (done.stderr or done.stdout or "").strip()
        try:
            parsed = json.loads(done.stdout or "{}")
            detail = str(parsed.get("stderr") or parsed.get("message") or parsed.get("reason")
                         or parsed.get("result_status") or detail)
        except ValueError:
            pass
        return False, f"Kit-Wechsel fehlgeschlagen (rc={done.returncode}, aktiv: {current}): {detail[-300:]}"
    return True, f"Branch gewechselt: {branch} (über agentic-kit transfer branch-switch)."
