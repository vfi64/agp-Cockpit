"""The Kit's own answer to „is a newer stable Kit release available?“ (AGP_KIT_RELEASE_CHECK_V1).

The Kit answers with ``kit status --check-release`` (KIT-GF-092, Kit 1.1.9). The Cockpit runs the
repository's own Kit, reads the ``release_check`` block and never asks the package index itself.
The Systemcheck line „Kit-Release“ and the task „Kit übernehmen“ (AGP_KIT_ADOPT_TASK_V1) both read it.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

KIT_RELEASE_TIMEOUT = 30          # the Kit limits its index request to 10 s

CURRENT, UPDATE_AVAILABLE, AHEAD, UNKNOWN = "CURRENT", "UPDATE_AVAILABLE", "AHEAD", "UNKNOWN"
# Cockpit-side outcomes when the Kit gives no usable verdict.
NO_KIT, NO_ANSWER, UNSUPPORTED, STALE_EDITABLE = "NO_KIT", "NO_ANSWER", "UNSUPPORTED", "STALE_EDITABLE"


@dataclass(frozen=True)
class KitRelease:
    result: str
    installed: str = ""      # what the Kit reports as installed
    latest: str = ""         # newest stable release at the workspace's index
    running: str = ""        # the running package's version (Cockpit's Kit discovery)
    editable: bool = False
    reason: str = ""

    @property
    def adoptable(self) -> bool:
        """A released wheel install with a newer stable release: „Kit übernehmen“ may start."""
        return self.result == UPDATE_AVAILABLE and not self.editable and bool(self.latest)


def read(root: Path, runner: Callable = subprocess.run) -> KitRelease:
    from agp_cockpit.core.kit_installation import discover
    root = Path(root)
    kit = discover(root)
    if kit is None:
        return KitRelease(NO_KIT, reason="kein Kit installiert")
    try:
        done = runner([str(kit.binary), "kit", "status", "--root", str(root), "--check-release", "--json"],
                      cwd=str(root), capture_output=True, text=True, timeout=KIT_RELEASE_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return KitRelease(NO_ANSWER, running=kit.version, reason=f"das Kit antwortet nicht ({type(exc).__name__})")
    text = f"{getattr(done, 'stdout', '') or ''}"
    try:
        data = json.loads(text[text.index("{"):])
    except ValueError:
        data = {}
    release = data.get("release_check") if isinstance(data, dict) else None
    if not isinstance(release, dict):
        if "check-release" in f"{text}{getattr(done, 'stderr', '') or ''}":   # Typer: No such option
            return KitRelease(UNSUPPORTED, running=kit.version, reason="Release-Prüfung erst ab Kit 1.1.9")
        return KitRelease(NO_ANSWER, running=kit.version, reason="das Kit lieferte keine Release-Prüfung")
    installed = str(release.get("installed") or "")
    editable = release.get("installation_kind") == "editable"
    result = str(release.get("result") or UNKNOWN)
    latest = str(release.get("latest_release") or "")
    if editable and installed and kit.version and installed != kit.version:
        # KIT-GF-093: the Kit compared the pip metadata of an editable install, not the running package.
        return KitRelease(STALE_EDITABLE, installed, latest, kit.version, True, result)
    return KitRelease(result, installed or kit.version, latest, kit.version, editable,
                      str(release.get("reason") or ""))


def info_text(release: KitRelease) -> str:
    """German text for the „Kit übernehmen“ information window when the task does not start."""
    if release.result == CURRENT:
        return f"Kit {release.installed} ist das neueste stabile Release. Nichts zu übernehmen."
    if release.result == AHEAD:
        return (f"Kit {release.installed} ist neuer als das neueste Release {release.latest}"
                + (" (Entwicklerinstallation)." if release.editable else ".") + " Nichts zu übernehmen.")
    if release.result == UPDATE_AVAILABLE and release.editable:
        return (f"Neu: Kit {release.latest}. Dies ist eine Entwicklerinstallation (Kit-Repository): "
                "dort zieht „Wiederherstellen“ main nach; „Kit übernehmen“ gilt für installierte Kit-Versionen.")
    if release.result == STALE_EDITABLE:
        return (f"Das Kit meldet {release.installed} aus veralteten Paketdaten, es läuft {release.running} "
                f"(neuestes Release {release.latest or 'unbekannt'}). Das Ergebnis ist nicht belastbar "
                "(Kit-Befund KIT-GF-093); nichts zu übernehmen.")
    if release.result == NO_KIT:
        return "Kein Kit installiert — erst das Kit installieren."
    if release.result == UNSUPPORTED:
        return (f"Kit {release.running} kennt die Release-Prüfung noch nicht (ab Kit 1.1.9). "
                "Diese eine Übernahme bitte mit Claude.")
    reason = release.reason or "unbekannt"
    return f"Der Release-Stand ist nicht prüfbar ({reason}). Netzverbindung prüfen und später erneut versuchen."
