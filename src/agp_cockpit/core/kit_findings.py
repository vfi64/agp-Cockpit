"""Kit findings register for the System tab (AGP_KIT_FINDINGS_VIEW_V1).

Source of truth: ``docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json``
(families). The Cockpit only reads it; a status changes in the register with
evidence (``fixed_in``, ``verified_by``). The effective status additionally
compares ``fixed_in`` with the installed Kit version, so "fixed in the Kit but
not installed here" is visible.

AGP_KIT_FINDING_REPRODUCED_V1: ``reproduced_in`` names the Kit version in
which the Cockpit's own retest still shows the defect. A Kit closure whose
``fixed_in`` is not newer than that version does not count as a fix; the
finding stays open until a later Kit release claims (and a retest confirms)
the fix.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REGISTER = Path("docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json")
SEVERITY_ORDER = {"critical": 0, "major": 1, "high": 1, "medium-high": 2, "medium": 3, "low": 4}

OPEN = "offen"
IN_PROGRESS = "im Kit in Arbeit"
FIXED_NOT_INSTALLED = "behoben, nicht installiert"
FIXED_UNVERIFIED = "behoben, nicht bestätigt"
VERIFIED = "bestätigt behoben"


@dataclass(frozen=True)
class KitFinding:
    id: str
    title: str
    severity: str
    status: str
    first_observed: str
    fixed_in: str = ""
    verified_by: str = ""
    reproduced_in: str = ""                     # AGP_KIT_FINDING_REPRODUCED_V1
    details: dict = field(default_factory=dict)
    mitigations: tuple = ()
    extensions: tuple = ()
    kit: dict = field(default_factory=dict)     # AGP_KIT_FINDINGS_SYNC_V1 statement of the Kit repo

    def effective_status(self, installed: str | None) -> str:
        if self.status == "VERIFIED_FIXED":
            return VERIFIED
        fixed_in = self.fixed_in
        fixed = self.status == "FIXED" or bool(fixed_in)
        if not fixed and self.kit.get("kit_state") == "CLOSED" and not self._kit_closure_refuted():
            fixed, fixed_in = True, str(self.kit.get("fixed_in") or "")
        if fixed:
            if installed and fixed_in and _version(installed) >= _version(fixed_in):
                return FIXED_UNVERIFIED
            return FIXED_NOT_INSTALLED
        if self.kit.get("kit_state") == "PARTIAL":
            return IN_PROGRESS
        return OPEN

    def _kit_closure_refuted(self) -> bool:
        """The Cockpit reproduced the defect in a Kit at least as new as the Kit's claimed fix."""
        if not self.reproduced_in:
            return False
        kit_fixed = str(self.kit.get("fixed_in") or "")
        return not kit_fixed or _version(kit_fixed) <= _version(self.reproduced_in)

    def detail_text(self, installed: str | None) -> str:
        lines = [f"{self.id} — {self.title}", "",
                 f"Status: {self.effective_status(installed)} (Register: {self.status}"
                 + (f", behoben in {self.fixed_in}" if self.fixed_in else "") + ")",
                 f"Schwere: {self.severity} · zuerst gesehen: {self.first_observed or '?'}"]
        if self.verified_by:
            lines.append(f"Bestätigt durch: {self.verified_by}")
        if self.reproduced_in:
            lines.append(f"Im Cockpit nachgetestet: Fehler besteht mit Kit {self.reproduced_in} weiter"
                         + (" — der Kit-Abschluss zählt nicht als Behebung." if self._kit_closure_refuted() else "."))
        if self.kit:
            lines.append(
                f"Kit-Repo: {self.kit.get('kit_state')} — {self.kit.get('raw')} ({self.kit.get('report')}, "
                f"{self.kit.get('date')})" + (f"; behoben in {self.kit['fixed_in']}" if self.kit.get("fixed_in") else ""))
        for key, label in (("expected", "Erwartet"), ("observed", "Beobachtet"), ("impact", "Wirkung"),
                           ("workaround", "Umgehung"), ("repair", "Reparatur im Kit"),
                           ("regression", "Prüfkriterium"), ("required_action", "Nötige Aktion"),
                           ("summary", "Zusammenfassung"), ("current_repair_status", "Reparaturstand")):
            value = self.details.get(key)
            if value:
                lines += ["", f"{label}:", _text(value)]
        for item in self.mitigations:
            lines += ["", f"Cockpit überbrückt ({item.get('date', '?')}, {item.get('marker', '')}):",
                      _text(item.get("description", ""))]
        for item in self.extensions:
            lines += ["", f"Weitere Beobachtung {item.get('date', '?')}: {item.get('title', '')}",
                      _text(item.get("observed", ""))]
        evidence = self.details.get("evidence")
        if evidence:
            lines += ["", "Nachweise:"] + [f"  · {e}" for e in (evidence if isinstance(evidence, list) else [evidence])]
        return "\n".join(lines)


def _text(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"  · {_text(v)}" for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", str(text))[:4]) or (0,)


def load(repository_root: Path) -> list[KitFinding]:
    from agp_cockpit.core.kit_findings_sync import load_overlay
    path = Path(repository_root) / REGISTER
    data = json.loads(path.read_text(encoding="utf-8"))
    overlay = (load_overlay(repository_root).get("findings") or {})
    findings = []
    for family in data.get("families") or []:
        if not isinstance(family, dict) or not family.get("id"):
            continue
        findings.append(KitFinding(
            id=str(family["id"]),
            title=str(family.get("title") or family.get("summary") or ""),
            severity=str(family.get("severity") or "").lower(),
            status=str(family.get("status") or "OPEN").upper(),
            first_observed=str(family.get("first_observed") or ""),
            fixed_in=str(family.get("fixed_in") or ""),
            verified_by=_text(family.get("verified_by") or ""),
            reproduced_in=str(family.get("reproduced_in") or ""),
            details=family,
            mitigations=tuple(m for m in family.get("cockpit_mitigation") or () if isinstance(m, dict)),
            extensions=tuple(e for e in family.get("extensions") or () if isinstance(e, dict)),
            kit=dict(overlay.get(str(family["id"])) or family.get("kit_repo_status") or {}),
        ))
    findings.sort(key=lambda f: (f.effective_status(None) != OPEN, SEVERITY_ORDER.get(f.severity, 5), f.id))
    return findings


def summary(findings: list[KitFinding], installed: str | None) -> str:
    states = [f.effective_status(installed) for f in findings]
    return (f"{len(findings)} Befunde · {states.count(OPEN)} offen · {states.count(IN_PROGRESS)} im Kit in Arbeit · "
            f"{states.count(FIXED_NOT_INSTALLED)} behoben, nicht installiert · "
            f"{states.count(FIXED_UNVERIFIED)} behoben, nicht bestätigt · {states.count(VERIFIED)} bestätigt behoben")
