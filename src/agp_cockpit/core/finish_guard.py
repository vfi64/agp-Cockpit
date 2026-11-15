"""„Abschließen“ publishes; it does not change the work (AGP_FINISH_PUBLISHES_ONLY_V1).

Live 2026-10-07 (PR #272, step 1839): the CI of the work branch was red; the remote
repair inside „Abschließen“ weakened three test assertions, committed them and
pushed again. Repairing code belongs to an „Arbeiten“ task the owner reads; the
finish task only commits work that was already there at its start and publishes it.

Before a work order of an „Abschließen“ mission runs, the bridge checks it:

* a work order may not name a file under ``tests/`` or ``src/`` (no reading for a
  repair, no writing, no sed): a correctable rejection names the rule;
* a commit-producing Kit command is allowed only when the work branch had
  uncommitted work when the mission started (an „Arbeiten“ task leaves it so).

The start state is recorded when the mission's first work order arrives, before
anything of that mission ran.

AGP_FINISH_PUBLISH_EXISTING_V1 (workflow-friction plan C3, V8, live 2026-11-13): the work was
already committed, so the branch was clean when „Abschließen“ started. The Kit's finish
orchestrator then still needed ``--path`` and this guard forbade a new commit: no way out. Kit
1.4.0 publishes the existing commits when its finish orchestrator gets no path selection (K1).
The guard stays; on a clean start it now also rejects a finish call that selects paths and names
the call, its line and the way out. ``existing_commits`` gives the finish prompt the state.
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
from pathlib import Path

FINISH_TITLE = "Standard · Abschließen"
PROTECTED_PATH = re.compile(r"""["'](?:\./)?(?:tests|src)/""")
COMMITTING = frozenset({"agentic-kit transfer commit"})
FINISHING = "agentic-kit work finish"
PATH_OPTION = "--path"
K1_KIT = (1, 4, 0)


def is_finish_mission(title: str) -> bool:
    return str(title or "").startswith(FINISH_TITLE)


def _dirty(repo_root: Path) -> list[str]:
    try:
        done = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo_root), text=True,
                              capture_output=True, timeout=30, check=False,
                              env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [line for line in (done.stdout or "").splitlines()
            if line.strip() and not line[3:].startswith("Download/")]


def _git(repo_root: Path, *args: str) -> str:
    try:
        done = subprocess.run(["git", *args], cwd=str(repo_root), text=True, capture_output=True,
                              timeout=30, check=False, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"))
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (done.stdout or "").strip() if done.returncode == 0 else ""


def existing_commits(repo_root: Path) -> dict | None:
    """AGP_FINISH_PUBLISH_EXISTING_V1: a work branch that is clean (Download/ aside) and carries
    commits origin/main lacks. ``published`` is ``none`` (no origin/<branch>), ``head`` (it is at
    HEAD) or ``older``. None for main, a detached HEAD, uncommitted work or nothing to publish."""
    branch = _git(repo_root, "branch", "--show-current")
    if not branch or branch in ("main", "master") or _dirty(repo_root):
        return None
    count = _git(repo_root, "rev-list", "--count", "refs/remotes/origin/main..HEAD")
    if not count.isdigit() or int(count) == 0:
        return None
    remote = _git(repo_root, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch}")
    head = _git(repo_root, "rev-parse", "HEAD")
    published = "none" if not remote else ("head" if remote == head else "older")
    return {"branch": branch, "commits": int(count), "published": published}


def kit_publishes_existing(version: str) -> bool | None:
    """K1 is in the Kit from 1.4.0 on; None when the version is unknown or unreadable."""
    numbers = re.match(r"^(\d+)\.(\d+)\.(\d+)", str(version or "").strip())
    if numbers is None:
        return None
    return tuple(int(n) for n in numbers.groups()) >= K1_KIT


def path_selections(content: str) -> list[str]:
    """Finish calls of a work order that select paths: the call writes ``--path`` itself, or
    ``--path`` stands free in the code (``ARGS += ["--path", p]``), with the call and its line."""
    from agp_cockpit.core.kit_command_catalog import (
        _located_invocations,
        _program,
        _subcommands,
        call_flags,
        free_execute_flags,
        render_call,
    )
    try:
        tree = ast.parse(content or "")
    except SyntaxError:
        return []
    free = free_execute_flags(tree, (PATH_OPTION,))
    found = []
    for argv, line in _located_invocations(tree):
        if _program(argv[0]) != "agentic-kit" or _subcommands(argv)[:2] != ["work", "finish"]:
            continue
        if PATH_OPTION in call_flags(argv):
            found.append(f"line {line}: {render_call(argv)}")
        elif free:
            lines = ", ".join(str(n) for _, n in free)
            found.append(f"line {line}: {render_call(argv)} ({PATH_OPTION} frei in line {lines})")
    return found


def start_state(runtime_root: Path, mission_id: str, repo_root: Path) -> dict:
    """The work tree at the mission's first work order (recorded once per mission)."""
    path = Path(runtime_root) / "finish-start.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if data.get("mission_id") != mission_id:
        data = {"mission_id": mission_id, "dirty": _dirty(repo_root)}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")
    return data


def violations(content: str, start: dict, kit_commands: list[str]) -> list[str]:
    found = []
    if PROTECTED_PATH.search(content or ""):
        found.append("„Abschließen“ veröffentlicht nur; ein Arbeitsauftrag darf hier keine Datei unter tests/ "
                     "oder src/ nennen (lesen, ändern oder prüfen). Code- und Testreparaturen gehören in einen "
                     "Arbeiten-Auftrag, den der Mensch liest (AGP_FINISH_PUBLISHES_ONLY_V1)")
    committing = sorted({name for name in kit_commands if name in COMMITTING})
    if committing and not start.get("dirty"):
        found.append("der Arbeitsbranch war beim Start von „Abschließen“ sauber; ein Commit ist hier nicht "
                     f"erlaubt ({', '.join(committing)}). Veröffentliche die vorhandenen Commits "
                     "(AGP_FINISH_PUBLISHES_ONLY_V1)")
    if FINISHING in kit_commands and not start.get("dirty"):
        selected = path_selections(content)
        if selected:
            found.append("der Arbeitsbranch war beim Start von „Abschließen“ sauber; die vorhandenen Commits "
                         "veröffentlicht das Kit selbst, wenn sein Finish-Orchestrator keine Pfade bekommt "
                         f"(K1, ab Kit 1.4.0). Ohne {PATH_OPTION} wiederholen: {'; '.join(selected)} "
                         "(AGP_FINISH_PUBLISH_EXISTING_V1)")
    return found
