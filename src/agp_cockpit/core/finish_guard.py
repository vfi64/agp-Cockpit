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
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

FINISH_TITLE = "Standard · Abschließen"
PROTECTED_PATH = re.compile(r"""["'](?:\./)?(?:tests|src)/""")
COMMITTING = frozenset({"agentic-kit transfer commit"})


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
    return found
