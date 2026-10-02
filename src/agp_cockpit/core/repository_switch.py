"""Repository switch (plan P4, AGP_REPOSITORY_SWITCH_V1).

The Cockpit steers one repository at a time. Switching is a Cockpit-level
event, never a repository change:

* ``check`` reads a candidate (git work tree, origin, installed Kit, Kit
  workspace, gh login) without running Kit commands or network reads;
* ``provision`` prepares only the Cockpit's own transport paths in a Kit
  workspace that is not the Cockpit's source checkout: ``Download/`` with the
  canonical ``run_next.py`` and local excludes in the repository's
  ``info/exclude`` (git's per-clone ignore file, never committed), so the
  transport paths stay out of ``git status`` and out of the Kit's
  clean-worktree checks; tracked files are never written;
* the switch itself persists the new root and restarts the app, so bridge,
  Download/run_next, command digest and Lagebericht are rebound by the normal
  start path (no hot rebinding of a running bridge).

The recent list lives beside the settings (``recent-repositories.json``).
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

RECENT_LIMIT = 8
RECENT_FILE = "recent-repositories.json"
TRANSPORT_EXCLUDES = ("/Download/", "/.local/agp-cockpit/")
WORKSPACE_MARKERS = (".agentic/config.yaml", ".agentic/project.yaml")


def _git(root: Path, *args: str, runner=subprocess.run) -> subprocess.CompletedProcess | None:
    try:
        return runner(["git", *args], cwd=str(root), text=True, capture_output=True,
                      timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _out(done) -> str:
    return (done.stdout or "").strip() if done is not None and done.returncode == 0 else ""


def is_git_work_tree(root: Path, *, runner=subprocess.run) -> bool:
    return Path(root).is_dir() and _out(_git(root, "rev-parse", "--is-inside-work-tree",
                                              runner=runner)) == "true"


def is_cockpit_checkout(root: Path) -> bool:
    """The Cockpit's own source checkout carries its extension and runner."""
    root = Path(root)
    return (root / "chrome_extension" / "manifest.json").is_file() and \
        (root / "Download" / "run_next.py").is_file()


@dataclass(frozen=True)
class SwitchCheck:
    root: str
    blockers: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    facts: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.blockers

    def text(self) -> str:
        lines = [f"Repository: {self.root}"]
        for key, label in (("branch", "Branch"), ("origin", "origin"), ("kit", "Kit"),
                           ("workspace", "Kit-Steuerschicht"), ("gh", "gh")):
            if key in self.facts:
                lines.append(f"{label}: {self.facts[key]}")
        lines += [f"✗ {b}" for b in self.blockers] + [f"! {w}" for w in self.warnings]
        if self.ok:
            lines.append("Wechsel möglich. Danach startet das Cockpit neu; beginne im neuen Repo "
                         "mit einem neuen ChatGPT-Chat.")
        return "\n".join(lines)


def check(candidate: Path, *, current: Path | None = None, runner=subprocess.run,
          kit_discover=None, gh_status=None) -> SwitchCheck:
    """Read-only check of a candidate repository (no Kit command, no network)."""
    root = Path(candidate).expanduser().resolve()
    if not root.is_dir():
        return SwitchCheck(str(root), blockers=("Ordner existiert nicht.",))
    if current is not None and root == Path(current).expanduser().resolve():
        return SwitchCheck(str(root), blockers=("Das ist bereits das aktuelle Repository.",))
    if not is_git_work_tree(root, runner=runner):
        return SwitchCheck(str(root), blockers=("Kein git-Repository.",))
    facts: dict = {}
    blockers: list[str] = []
    warnings: list[str] = []
    facts["branch"] = _out(_git(root, "branch", "--show-current", runner=runner)) or "(detached)"
    origin = _out(_git(root, "remote", "get-url", "origin", runner=runner))
    facts["origin"] = origin or "fehlt"
    if not origin:
        blockers.append("Kein Remote „origin“ — Abschließen und CI brauchen ein GitHub-Repository.")
    if kit_discover is None:
        from agp_cockpit.core.kit_installation import discover as kit_discover
    kit = kit_discover(root)
    facts["kit"] = (kit.version or "?") if kit is not None else "nicht installiert"
    if kit is None:
        warnings.append("Agentic Project Kit ist nicht installiert (<repo>/.venv/bin/agentic-kit oder "
                        "im PATH) — danach Zustand UNKLAR, keine Tasks.")
    workspace = any((root / marker).is_file() for marker in WORKSPACE_MARKERS)
    facts["workspace"] = "ja" if workspace else "nein"
    if not workspace:
        warnings.append("Keine Kit-Steuerschicht (.agentic/config.yaml) — danach Zustand KEIN_KIT; "
                        "„Repo übernehmen“ folgt mit Plan P9.")
    if gh_status is None:
        gh_status = _gh_logged_in
    logged_in = gh_status(root)
    facts["gh"] = {True: "angemeldet", False: "nicht angemeldet", None: "nicht gefunden"}[logged_in]
    if logged_in is False:
        warnings.append("gh ist nicht angemeldet (gh auth login) — danach Zustand UNKLAR.")
    if _out(_git(root, "status", "--porcelain", runner=runner)):
        warnings.append("Das Arbeitsverzeichnis hat offene Änderungen — die Lage zeigt danach, "
                        "was zu tun ist.")
    return SwitchCheck(str(root), tuple(blockers), tuple(warnings), facts)


def _gh_logged_in(root: Path) -> bool | None:
    from agp_cockpit.core.ci_gate import gh_binary
    gh = gh_binary(root)
    if not gh:
        return None
    try:
        return subprocess.run([gh, "auth", "status"], cwd=str(root), capture_output=True,
                              text=True, timeout=20, check=False).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return None


# --- provisioning of the Cockpit's transport paths ------------------------------

def canonical_runner() -> Path | None:
    """The versioned run_next.py of this Cockpit (source checkout or app bundle)."""
    candidates = [Path(__file__).resolve().parents[3] / "Download" / "run_next.py"]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "runner" / "run_next.py")
    return next((c for c in candidates if c.is_file()), None)


def provision(root: Path, *, runner_source: Path | None = None,
              git_runner=subprocess.run) -> list[str]:
    """Prepare Download/run_next.py and local excludes; return what was done.

    Never writes tracked files: in the Cockpit's own checkout (tracked runner)
    nothing happens; a tracked Download/run_next.py elsewhere is left alone.
    """
    root = Path(root).expanduser().resolve()
    if is_cockpit_checkout(root):
        return []
    actions: list[str] = []
    runner_source = runner_source or canonical_runner()
    if runner_source is None:
        raise FileNotFoundError("canonical run_next.py of the Cockpit not found")
    target = root / "Download" / "run_next.py"
    tracked = _git(root, "ls-files", "--error-unmatch", "Download/run_next.py", runner=git_runner)
    if tracked is not None and tracked.returncode == 0:
        raise PermissionError("Download/run_next.py is tracked in this repository; not overwritten")
    source_bytes = runner_source.read_bytes()
    if not target.is_file() or target.read_bytes() != source_bytes:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source_bytes)
        actions.append("Download/run_next.py angelegt")
    exclude_rel = _out(_git(root, "rev-parse", "--git-path", "info/exclude", runner=git_runner))
    if not exclude_rel:
        raise RuntimeError("git info/exclude path not readable")
    exclude = (root / exclude_rel).resolve() if not Path(exclude_rel).is_absolute() else Path(exclude_rel)
    existing = exclude.read_text(encoding="utf-8").splitlines() if exclude.is_file() else []
    missing = [entry for entry in TRANSPORT_EXCLUDES if entry not in existing]
    if missing:
        exclude.parent.mkdir(parents=True, exist_ok=True)
        lines = existing + ["# AGP Cockpit transport paths (local only, never committed)", *missing]
        exclude.write_text("\n".join(lines) + "\n", encoding="utf-8")
        actions.append("lokale Ausnahmen in .git/info/exclude: " + ", ".join(missing))
    return actions


# --- recent list ----------------------------------------------------------------

def recent_path(app_support: Path) -> Path:
    return Path(app_support) / RECENT_FILE


def load_recent(app_support: Path) -> list[str]:
    try:
        data = json.loads(recent_path(app_support).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [str(p) for p in data if isinstance(p, str)][:RECENT_LIMIT] if isinstance(data, list) else []


def remember(app_support: Path, root: Path) -> list[str]:
    entry = str(Path(root).expanduser().resolve())
    items = [entry] + [p for p in load_recent(app_support) if p != entry]
    items = items[:RECENT_LIMIT]
    path = recent_path(app_support)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=1) + "\n", encoding="utf-8")
    return items
