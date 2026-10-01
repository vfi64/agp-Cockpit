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


def start_block_reason(repository_root: Path) -> str:
    """Empty when tasks may start; otherwise the operator-facing reason."""
    freshness = check(repository_root)
    return f"Blockiert — {freshness.message}" if freshness.stale else ""
