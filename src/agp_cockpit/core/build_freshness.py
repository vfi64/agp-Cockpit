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


_BUILD = re.compile(r"^release-(\d+(?:\.\d+)*)(?:-r(\d+))?$")


def build_order(left: str, right: str) -> int | None:
    """-1/0/1 when both are release build ids (release-<app>[-r<N>]), else None.

    AGP_BUILD_ORDER_V1 (live 2026-10-07, r11): „Abschließen“ switched to main before
    pulling it; for two seconds the checkout carried the older r10 and the guard said
    „Quellstand (r10) ist neuer als die laufende App (r11)“. An older source or bundle
    is no reason to rebuild.
    """
    a, b = _BUILD.match(str(left or "")), _BUILD.match(str(right or ""))
    if not a or not b:
        return None
    key = lambda m: (tuple(int(x) for x in m.group(1).split(".")), int(m.group(2) or 0))  # noqa: E731
    return (key(a) > key(b)) - (key(a) < key(b))


def check(repository_root: Path, running: str = BRIDGE_BUILD_ID, *,
          frozen: bool | None = None) -> BuildFreshness:
    root = Path(repository_root)
    if frozen is None:
        frozen = bool(getattr(sys, "frozen", False))
    # A run from source is not the bundle; only the packaged app compares with it.
    bundle = _read(root / BUNDLE_ID_FILE, _BUNDLE) if frozen else ""
    source = _read(root / SOURCE_ID_FILE, _SOURCE)
    if bundle and bundle != running and build_order(bundle, running) != -1:
        return BuildFreshness(running, bundle, source, True,
                              f"Neuer Build vorhanden ({bundle}), diese App läuft noch mit {running}. "
                              "Cockpit mit Cmd+Q beenden und neu starten.")
    order = build_order(source, running) if source else None
    if source and source != running and order != -1:
        relation = (f"ist neuer als die laufende App ({running})" if order == 1
                    else f"passt nicht zur laufenden App ({running})")
        return BuildFreshness(running, bundle, source, True,
                              f"Quellstand ({source}) {relation}. "
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
    return stale_block_reason(repository_root, release_version=release_version) \
        or kit_block_reason(repository_root)


def stale_block_reason(repository_root: Path, *, release_version: str = "") -> str:
    """The build part of ``start_block_reason`` (file reads only; AGP_AMPEL_V1 polls it)."""
    freshness = check(freshness_root(repository_root))
    if freshness.stale and not _own_release_build(freshness, release_version):
        return f"Blockiert — {freshness.message}"
    return ""


def _own_release_build(freshness: BuildFreshness, release_version: str) -> bool:
    if not release_version or freshness.source != f"release-{release_version}":
        return False
    return not freshness.bundle or freshness.bundle == freshness.running
