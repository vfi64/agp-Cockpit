"""AGP_CI_CONFIG_GUARD_V1: a work order does not change the CI configuration on its own.

Live 2026-10-22 (Kit repository, step 65): a test failed in a pull request's CI, and the agent edited
`.github/workflows/ci.yml` locally to make it pass instead of reporting the failure. It asked before
committing, but the edit was made. A red check or a Kit BLOCKED is reported, never worked around
in the CI configuration.

The bridge records the CI configuration paths that differ from origin/main (or are uncommitted)
before a work order runs and again after it. A path that the work order newly changed stops the
mission (BLOCKED) unless the mission text names that path, so a task that is about the CI can
still change it. The change stays in the worktree for the owner to inspect.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

PROTECTED_PREFIXES = (".github/workflows/", ".agentic/ci/")


def _git_lines(root: Path, *args: str) -> list[str]:
    try:
        done = subprocess.run(["git", *args], cwd=str(root), text=True, capture_output=True,
                              timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if getattr(done, "returncode", 1) != 0:   # unreadable: no evidence of a change
        return []
    return str(getattr(done, "stdout", "") or "").splitlines()


def changed_ci_paths(root: Path) -> set[str]:
    """CI configuration paths that are uncommitted or committed on the branch but not in origin/main."""
    names = {line[3:].split(" -> ")[-1] for line in _git_lines(root, "status", "--porcelain",
                                                                "--untracked-files=all") if len(line) > 3}
    names |= set(_git_lines(root, "diff", "--name-only", "origin/main...HEAD"))
    return {name for name in names if name.startswith(PROTECTED_PREFIXES)}


def violation(before: set[str], after: set[str], mission_text: str) -> str:
    """The stop text when the work order newly changed CI configuration the mission does not name."""
    unasked = sorted(path for path in after - before if path not in str(mission_text or ""))
    if not unasked:
        return ""
    return ("CI-Konfiguration geändert, ohne dass der Auftrag sie nennt (AGP_CI_CONFIG_GUARD_V1): "
            + ", ".join(unasked) + ". Eine rote Prüfung oder ein Kit-BLOCKED wird gemeldet, nicht in der "
            "CI umgangen. Die Änderung liegt unverändert im Arbeitsbaum; prüfen und über "
            "„Wiederherstellen“ verwerfen oder den Auftrag mit dem Dateinamen neu stellen.")
