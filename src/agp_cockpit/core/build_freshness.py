"""The running app must be the build that is on disk.

AGP_STALE_APP_GUARD_V1 (live 2026-10-01): a rebuilt app was opened while the
old instance still ran; macOS only activated the old one (same bundle id), so
the new bridge and extension never started and a test ran against the old
build. The running app compares its own build id with the bundle on disk and
with the source tree; on a mismatch it shows a warning and refuses to start
tasks until it is restarted (or rebuilt).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from agp_cockpit.version import BRIDGE_BUILD_ID

BUNDLE_ID_FILE = Path(".local/agp-cockpit/dist/AGP Cockpit.app/Contents/Resources/chrome_extension/build_identity.js")
SOURCE_ID_FILE = Path("src/agp_cockpit/version.py")
_BUNDLE = re.compile(r'AGP_EXTENSION_BUILD_ID\s*=\s*"([^"]+)"')
_SOURCE = re.compile(r'BRIDGE_BUILD_ID\s*=\s*"([^"]+)"')


@dataclass(frozen=True)
class BuildFreshness:
    running: str
    bundle: str
    source: str
    stale: bool
    message: str


def _read(path: Path, pattern: re.Pattern) -> str:
    try:
        match = pattern.search(path.read_text(encoding="utf-8"))
    except OSError:
        return ""
    return match.group(1) if match else ""


def check(repository_root: Path, running: str = BRIDGE_BUILD_ID, *,
          frozen: bool | None = None) -> BuildFreshness:
    root = Path(repository_root)
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    # A run from source is not the bundle; only the packaged app compares with it.
    bundle = _read(root / BUNDLE_ID_FILE, _BUNDLE) if frozen else ""
    source = _read(root / SOURCE_ID_FILE, _SOURCE)
    if bundle and bundle != running:
        return BuildFreshness(running, bundle, source, True,
                              f"Neuer Build vorhanden ({bundle}), diese App läuft noch mit {running}. "
                              "Cockpit mit Cmd+Q beenden und neu starten.")
    if source and source != running:
        return BuildFreshness(running, bundle, source, True,
                              f"Quellstand ({source}) ist neuer als die laufende App ({running}). "
                              "App neu bauen, Cockpit mit Cmd+Q beenden und neu starten.")
    return BuildFreshness(running, bundle, source, False, "")


def cockpit_home() -> Path | None:
    """The Cockpit's own checkout: the app bundle lives in <home>/.local/…/dist,
    a source run in <home>/src/agp_cockpit."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return next((p.parent for p in exe.parents if p.name == ".local"), None)
    home = Path(__file__).resolve().parents[3]
    return home if (home / SOURCE_ID_FILE).is_file() else None


def freshness_root(repository_root: Path) -> Path:
    """AGP_REPOSITORY_SWITCH_V1: in another repository the guard still compares
    with the Cockpit's own checkout, not with the steered repository."""
    root = Path(repository_root)
    if (root / SOURCE_ID_FILE).is_file():
        return root
    return cockpit_home() or root


def kit_block_reason(repository_root: Path) -> str:
    """AGP_REPO_STATE_V1 (P2): no installed Kit, no task (fail closed)."""
    from agp_cockpit.core.kit_installation import discover
    if discover(Path(repository_root)) is None:
        return ("Blockiert — Agentic Project Kit ist nicht installiert (weder <repo>/.venv/bin/agentic-kit "
                "noch agentic-kit im Pfad). Der Lagebericht zeigt den Zustand.")
    return ""


def start_block_reason(repository_root: Path, *, release_version: str = "") -> str:
    """Empty when tasks may start; otherwise the operator-facing reason.

    AGP_RELEASE_PHASE2_APPROVAL_V1 (live 2026-10-05, release 0.2.0): phase 1 of a release
    sets the build id to ``release-<version>`` and merges it, so the running app counted as
    stale and refused the owner's approval of phase 2, which only publishes the tag (and the
    Kit's GitHub entry) and runs no new app code. ``release_version`` exempts exactly that
    source build id while the bundle on disk is still the running one."""
    freshness = check(freshness_root(repository_root))
    if freshness.stale and not _own_release_build(freshness, release_version):
        return f"Blockiert — {freshness.message}"
    return kit_block_reason(repository_root)


def _own_release_build(freshness: BuildFreshness, release_version: str) -> bool:
    if not release_version or freshness.source != f"release-{release_version}":
        return False
    return not freshness.bundle or freshness.bundle == freshness.running
