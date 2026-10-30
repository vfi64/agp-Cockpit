"""Cleanup of Cockpit working files with a preview (AGP_MAINTENANCE_CLEANUP_V1).

Live 2026-10-02: ``Download/alt`` held 973 MB (old Chrome test profiles,
87 MB bundles); browser copies piled up in ~/Downloads and Kit logs in /tmp.
One rule set, always previewed first, executed only on the operator's OK:

* ``Download/<step>_*``: kept for the newest ``keep_steps`` steps and for
  anything younger than ``max_age_days``; ``run_next.py`` is never touched;
* ``.local/agp-cockpit/delivery`` (result projections): older than
  ``max_age_days``;
* ``.local/agp-cockpit/tmp`` (TMPDIR of work orders): older than one day — of the selected
  repository and of every other repository in the Cockpit's runtime home (AGP_CLEANUP_ALL_REPOS_V1);
* ``.local/agp-cockpit/ci`` (CI evidence): older than ``max_age_days`` beyond
  the newest 20;
* the Kit's own temporary logs through ``agentic-kit artifact-gc --tmp-logs``
  (dry run in the preview, ``--execute`` on OK).

``~/Downloads`` is not scanned: the extension removes its own copies after the
bridge persisted them (AGP_DOWNLOAD_HYGIENE_V1). Execution deletes only files
that a fresh plan still lists.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

KEEP_STEPS = 50
MAX_AGE_DAYS = 30
TMP_AGE_SECONDS = 24 * 3600
KEEP_CI_EVIDENCE = 20
STEP_FILE = re.compile(r"^(\d+)_")


@dataclass(frozen=True)
class Candidate:
    path: Path
    bytes: int
    area: str


@dataclass(frozen=True)
class Plan:
    candidates: tuple[Candidate, ...]
    kit_argv: tuple[str, ...] | None
    kit_preview: str

    @property
    def total_bytes(self) -> int:
        return sum(c.bytes for c in self.candidates)


def _size(path: Path) -> int:
    """Bytes of regular files under ``path``; symbolic links are neither followed nor counted
    (pytest's ``…current`` links point into the same tree, AGP_CLEANUP_ALL_REPOS_V1)."""
    if path.is_symlink() or not path.exists():
        return 0
    if not path.is_dir():
        return path.stat().st_size
    total = 0
    for folder, _dirs, files in os.walk(path, followlinks=False):
        for name in files:
            try:
                info = os.lstat(os.path.join(folder, name))
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
    return total


def _other_runtime_tmp(local: Path) -> list[tuple[Path, str]]:
    """AGP_CLEANUP_ALL_REPOS_V1 (2026-10-29): the work-order temp folders of every repository the
    Cockpit steers live in its runtime home (AGP_RUNTIME_HOME_V1), one folder per repository.
    „Aufräumen“ saw only the selected repository's folder, so the Kit repository's pytest trees
    were never offered while the Cockpit's own repository was selected."""
    from agp_cockpit.core.runtime_paths import runtime_home_base
    base = runtime_home_base()
    if base is None:
        return []
    found = [(base / "tmp", "Temporär (Cockpit)")]
    repos = base / "repos"
    if repos.is_dir():
        found += [(repo / "tmp", f"Temporär ({repo.name.rsplit('-', 1)[0]})")
                  for repo in sorted(repos.iterdir()) if repo.is_dir() and not repo.is_symlink()]
    own = (local / "tmp").resolve()
    return [(folder, area) for folder, area in found if folder.is_dir() and folder.resolve() != own]


def _download_candidates(root: Path, now: float, keep_steps: int, max_age: float) -> list[Candidate]:
    download = root / "Download"
    if not download.is_dir():
        return []
    files = [(int(m.group(1)), p) for p in download.iterdir()
             if p.is_file() and p.name != "run_next.py" and (m := STEP_FILE.match(p.name))]
    steps = sorted({step for step, _ in files}, reverse=True)
    protected = set(steps[:keep_steps])
    return [Candidate(p, p.stat().st_size, "Download")
            for step, p in sorted(files)
            if step not in protected and now - p.stat().st_mtime > max_age]


def _aged(directory: Path, area: str, now: float, max_age: float, keep_newest: int = 0) -> list[Candidate]:
    if not directory.is_dir():
        return []
    entries = sorted(directory.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return [Candidate(p, _size(p), area) for p in entries[keep_newest:] if now - p.stat().st_mtime > max_age]


def plan(root: Path, *, now: float | None = None, keep_steps: int = KEEP_STEPS,
         max_age_days: int = MAX_AGE_DAYS, kit_binary: Path | None = None,
         runner=subprocess.run) -> Plan:
    root = Path(root).resolve()
    now = time.time() if now is None else now
    max_age = max_age_days * 86400
    from agp_cockpit.core.runtime_paths import runtime_base
    local = runtime_base(root)   # AGP_RUNTIME_HOME_V1
    candidates = (
        _download_candidates(root, now, keep_steps, max_age)
        + _aged(local / "delivery", "Zustellungen", now, max_age)
        + _aged(local / "tmp", "Temporär", now, TMP_AGE_SECONDS)
        + _aged(local / "ci", "CI-Nachweise", now, max_age, keep_newest=KEEP_CI_EVIDENCE)
    )
    for folder, area in _other_runtime_tmp(local):
        candidates += _aged(folder, area, now, TMP_AGE_SECONDS)
    # AGP_RUNTIME_HOME_V1: the Cockpit runtime that earlier builds left in a steered
    # repository is offered as a whole once the runtime lives in the Cockpit's home.
    legacy = root / ".local" / "agp-cockpit"
    if local != legacy and legacy.is_dir():
        candidates.append(Candidate(legacy, _size(legacy), "Alte Cockpit-Laufzeit im Repository"))
    kit_argv, preview = None, "Kit nicht gefunden — Kit-Logs werden nicht aufgeräumt."
    if kit_binary is not None:
        kit_argv = (str(kit_binary), "artifact-gc", "--tmp-logs")
        preview = _run_kit(root, list(kit_argv), runner)
    return Plan(tuple(candidates), kit_argv, preview)


def _run_kit(root: Path, argv: list[str], runner) -> str:
    from agp_cockpit.core.ci_gate import tool_env
    try:
        completed = runner(argv, cwd=str(root), env=tool_env(root), text=True,
                           capture_output=True, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"{type(exc).__name__}: {exc}"
    text = (completed.stdout or "") + (completed.stderr or "")
    return f"$ {' '.join(argv[1:])} → rc {completed.returncode}\n" + text.strip()[-2000:]


def describe(result: Plan) -> str:
    if not result.candidates:
        lines = ["Keine Cockpit-Dateien zum Löschen."]
    else:
        areas: dict[str, list[Candidate]] = {}
        for candidate in result.candidates:
            areas.setdefault(candidate.area, []).append(candidate)
        lines = [f"{len(result.candidates)} Einträge, {result.total_bytes / 1e6:.1f} MB:"]
        lines += [f"  · {area}: {len(items)} ({sum(c.bytes for c in items) / 1e6:.1f} MB)"
                  for area, items in areas.items()]
    lines += ["", "Kit (Vorschau):", result.kit_preview]
    return "\n".join(lines)


def execute(root: Path, approved: Plan, *, kit_binary: Path | None = None,
            runner=subprocess.run, now: float | None = None) -> dict:
    """Delete what the approved plan lists and a fresh plan still lists."""
    root = Path(root).resolve()
    fresh = {c.path for c in plan(root, now=now).candidates}
    from agp_cockpit.core.runtime_paths import runtime_base, runtime_home_base
    home = runtime_home_base()
    allowed = (root / "Download", runtime_base(root), root / ".local" / "agp-cockpit",
               *((home,) if home is not None else ()))
    deleted, freed, skipped = 0, 0, []
    for candidate in approved.candidates:
        path = candidate.path
        inside = any(path.resolve().is_relative_to(base.resolve()) for base in allowed)
        if path not in fresh or not inside or not path.exists():
            skipped.append(str(path))
            continue
        size = _size(path)
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)   # removes links inside the tree, never their targets
        else:
            path.unlink()
        deleted += 1
        freed += size
    kit_output = ""
    if approved.kit_argv is not None:
        kit_output = _run_kit(root, [*approved.kit_argv, "--execute"], runner)
    return {"deleted": deleted, "bytes": freed, "skipped": skipped, "kit_output": kit_output}
