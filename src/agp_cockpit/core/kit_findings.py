"""Kit findings register for the System tab (AGP_KIT_FINDINGS_VIEW_V1).

Source of truth: ``docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json``
(families). The Cockpit only reads it; a status changes in the register with
evidence (``fixed_in``, ``verified_by``). The effective status additionally
compares ``fixed_in`` with the installed Kit version, so "fixed in the Kit but
not installed here" is visible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

REGISTER = Path("docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json")
SEVERITY_ORDER = {"critical": 0, "major": 1, "high": 1, "medium-high": 2, "medium": 3, "low": 4}

OPEN = "offen"
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
    details: dict = field(default_factory=dict)
    mitigations: tuple = ()
    extensions: tuple = ()

    def effective_status(self, installed: str | None) -> str:
        if self.status == "VERIFIED_FIXED":
            return VERIFIED
        if self.status == "FIXED" or self.fixed_in:
            if installed and _version(installed) >= _version(self.fixed_in or "0"):
                return FIXED_UNVERIFIED
            return FIXED_NOT_INSTALLED
        return OPEN

    def detail_text(self, installed: str | None) -> str:
        lines = [f"{self.id} — {self.title}", "",
                 f"Status: {self.effective_status(installed)} (Register: {self.status}"
                 + (f", behoben in {self.fixed_in}" if self.fixed_in else "") + ")",
                 f"Schwere: {self.severity} · zuerst gesehen: {self.first_observed or '?'}"]
        if self.verified_by:
            lines.append(f"Bestätigt durch: {self.verified_by}")
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
    path = Path(repository_root) / REGISTER
    data = json.loads(path.read_text(encoding="utf-8"))
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
            details=family,
            mitigations=tuple(m for m in family.get("cockpit_mitigation") or () if isinstance(m, dict)),
            extensions=tuple(e for e in family.get("extensions") or () if isinstance(e, dict)),
        ))
    findings.sort(key=lambda f: (f.effective_status(None) != OPEN, SEVERITY_ORDER.get(f.severity, 5), f.id))
    return findings


def summary(findings: list[KitFinding], installed: str | None) -> str:
    states = [f.effective_status(installed) for f in findings]
    return (f"{len(findings)} Befunde · {states.count(OPEN)} offen · "
            f"{states.count(FIXED_NOT_INSTALLED)} behoben, nicht installiert · "
            f"{states.count(FIXED_UNVERIFIED)} behoben, nicht bestätigt · {states.count(VERIFIED)} bestätigt behoben")
