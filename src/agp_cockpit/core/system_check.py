"""Systemcheck: one read-only look at everything a task needs (plan item 5, owner 2026-10-05).

AGP_SYSTEM_CHECK_V1 (owner 2026-10-07: „Bei Problemzuständen soll das Cockpit den Nutzer selbst
auf dem Lösungsweg führen“): the System tab checks app build, bridge, Chrome extension, ChatGPT
UI variant, Agentic Kit, repository, GitHub CLI and disk space, and names for every problem the
one step that fixes it. Every check reads only; none changes the repository, the Kit or a task.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

OK, WARN, FAIL = "ok", "warn", "fail"
MIN_FREE_BYTES = 2 * 1024 ** 3
_PIN = re.compile(r"agentic-project-kit==(\d+\.\d+\.\d+)")


@dataclass(frozen=True)
class Check:
    name: str
    level: str          # ok | warn | fail
    detail: str
    fix: str = ""


def _app_build(root: Path) -> Check:
    from agp_cockpit.core.build_freshness import check, freshness_root
    fresh = check(freshness_root(root))
    if fresh.stale:
        return Check("App-Build", FAIL, fresh.message, "Oben „Neu bauen und neu starten“ klicken.")
    if fresh.note:
        return Check("App-Build", WARN, fresh.note)
    return Check("App-Build", OK, f"{fresh.running} läuft und passt zum Quellstand")


def _bridge(_root: Path) -> Check:
    from agp_cockpit.core.mission_http_client import status
    try:
        mission = (status() or {}).get("mission") or {}
    except Exception as exc:  # noqa: BLE001 - reported, never raised
        return Check("Bridge", FAIL, f"nicht erreichbar ({type(exc).__name__})",
                     "Cockpit mit Cmd+Q beenden und neu starten.")
    state = str(mission.get("state") or "keine Mission")
    return Check("Bridge", OK, f"erreichbar · letzte Mission: {state} · {mission.get('title') or '—'}")


EXTENSION_FIXES = {
    "fresh-extension-handshake-missing": "Den ChatGPT-Tab in Chrome öffnen bzw. neu laden.",
    "handshake-stale": "Den ChatGPT-Tab in Chrome neu laden.",
    "handshake-build-id-mismatch": "Ein paar Sekunden warten; sonst den ChatGPT-Tab neu laden.",
    "handshake-version-mismatch": "Ein paar Sekunden warten; sonst den ChatGPT-Tab neu laden.",
    "staged-build-id-mismatch": "Oben „Neu bauen und neu starten“ klicken.",
    "staged-version-mismatch": "Oben „Neu bauen und neu starten“ klicken.",
    "staged-extension-identity-missing": "Oben „Neu bauen und neu starten“ klicken.",
    "run-next-missing": "„Repo wechseln …“ auf dieses Repository erneut ausführen.",
}


def _extension(root: Path) -> Check:
    from agp_cockpit.adapters.macos_settings import bridge_runtime_root
    from agp_cockpit.core.runtime_identity import runtime_identity_status
    identity = runtime_identity_status(root, bridge_runtime_root())
    if identity.get("ready"):
        return Check("Chrome-Erweiterung", OK, f"meldet Build {identity.get('handshake_build_id') or '?'}")
    reasons = [str(r) for r in identity.get("reasons", [])]
    fix = next((EXTENSION_FIXES[r] for r in reasons if r in EXTENSION_FIXES),
               "Den ChatGPT-Tab neu laden; hilft das nicht, Claude die Gründe nennen.")
    return Check("Chrome-Erweiterung", FAIL, "nicht bereit: " + ", ".join(reasons), fix)


def _ui_variant(root: Path) -> Check:
    from agp_cockpit.core.ui_observation import variant_line
    line = variant_line(root)
    level = WARN if "NEU" in line else OK
    return Check("ChatGPT-Oberfläche", level, line.split(": ", 1)[-1],
                 "Neu erkannte Oberfläche: beim nächsten Fehler Claude den Schnappschuss nennen." if level == WARN else "")


def ci_kit_pins(root: Path) -> set[str]:
    """The Kit versions the repository's GitHub workflows install (``agentic-project-kit==X``)."""
    pins: set[str] = set()
    for workflow in (Path(root) / ".github" / "workflows").glob("*.y*ml"):
        try:
            pins.update(_PIN.findall(workflow.read_text(encoding="utf-8")))
        except OSError:
            continue
    return pins


def kit_ci_mismatch(root: Path) -> str:
    """AGP_RELEASE_KIT_MATCHES_CI_V1: "" when the installed Kit is one the CI installs (or the CI pins
    none); otherwise a German sentence naming both versions."""
    from agp_cockpit.core.kit_installation import discover
    kit = discover(Path(root))
    pins = ci_kit_pins(Path(root))
    if kit is None or not pins or kit.version in pins:
        return ""
    return f"lokal ist Kit {kit.version} installiert, die CI nutzt {', '.join(sorted(pins))}"


def _kit(root: Path) -> Check:
    from agp_cockpit.core.build_freshness import freshness_root
    from agp_cockpit.core.kit_installation import discover
    kit = discover(root)
    if kit is None:
        return Check("Agentic Kit", FAIL, "nicht installiert (weder .venv/bin/agentic-kit noch im Pfad)",
                     "Kit im Repository installieren (siehe Lagebericht).")
    pins = ci_kit_pins(freshness_root(root))
    if pins and kit.version not in pins:
        return Check("Agentic Kit", WARN, f"installiert {kit.version}, die CI des Cockpits nutzt {', '.join(sorted(pins))}",
                     "Kit-Version angleichen (Übernahme einer neuen Kit-Version mit Claude).")
    stale = getattr(kit, "metadata_version", "")
    note = (f" · Entwicklerinstallation (Paketangabe {stale})" if stale and stale != kit.version else "")
    return Check("Agentic Kit", OK, f"{kit.version}" + (" · wie in der CI" if pins else "") + note)


def _repository(root: Path) -> Check:
    from agp_cockpit.core.work_facts import facts_line, observe
    facts = observe(root)
    line = facts_line(facts).replace("Vom Cockpit geprüft: ", "")
    if not facts.ok:
        return Check("Repository", FAIL, line, "Repository-Pfad prüfen („Repo wechseln …“).")
    if facts.uncommitted:
        return Check("Repository", WARN, line, "Offene Änderungen: abschließen oder bewusst verwerfen.")
    return Check("Repository", OK, line)


def _github_cli(root: Path, runner: Callable = subprocess.run) -> Check:
    from agp_cockpit.core.ci_gate import gh_binary
    gh = gh_binary(root)
    if not gh:
        return Check("GitHub-CLI", WARN, "gh nicht gefunden — das Cockpit kann CI und PRs nicht selbst prüfen",
                     "GitHub CLI installieren: brew install gh, dann gh auth login.")
    try:
        done = runner([gh, "auth", "status"], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return Check("GitHub-CLI", WARN, f"gh antwortet nicht ({type(exc).__name__})", "Im Terminal gh auth status prüfen.")
    if done.returncode != 0:
        return Check("GitHub-CLI", FAIL, "gh ist nicht angemeldet", "Im Terminal: gh auth login")
    return Check("GitHub-CLI", OK, "angemeldet")


def _disk(root: Path) -> Check:
    from agp_cockpit.core.runtime_paths import runtime_base
    base = runtime_base(root)
    probe = base if base.exists() else Path(root)
    free = shutil.disk_usage(probe).free
    gb = free / 1024 ** 3
    if free < MIN_FREE_BYTES:
        return Check("Speicherplatz", WARN, f"nur {gb:.1f} GB frei", "System → „Aufräumen …“ nutzen oder Platz schaffen.")
    return Check("Speicherplatz", OK, f"{gb:.0f} GB frei")


CHECKS: tuple[Callable[[Path], Check], ...] = (
    _app_build, _bridge, _extension, _ui_variant, _kit, _repository, _github_cli, _disk)
NAMES = ("App-Build", "Bridge", "Chrome-Erweiterung", "ChatGPT-Oberfläche", "Agentic Kit", "Repository",
         "GitHub-CLI", "Speicherplatz")


def run_all(repository_root: Path, checks=CHECKS) -> list[Check]:
    """Every check, in order; a check that raises is reported as failed, never raised."""
    root = Path(repository_root)
    results = []
    for index, check in enumerate(checks):
        try:
            results.append(check(root))
        except Exception as exc:  # noqa: BLE001 - a broken check is a finding, not a crash
            name = NAMES[index] if index < len(NAMES) else getattr(check, "__name__", "Prüfung")
            results.append(Check(name, FAIL, f"Prüfung selbst fehlgeschlagen: {type(exc).__name__}: {exc}"[:300],
                                 "Claude den Text nennen."))
    return results


def summary(results: list[Check]) -> str:
    fails = sum(r.level == FAIL for r in results)
    warns = sum(r.level == WARN for r in results)
    when = time.strftime("%H:%M:%S")
    if fails:
        return f"Systemcheck {when}: {fails} Problem(e), {warns} Hinweis(e) — Lösungswege stehen dabei."
    if warns:
        return f"Systemcheck {when}: alles nutzbar, {warns} Hinweis(e)."
    return f"Systemcheck {when}: alles in Ordnung."
