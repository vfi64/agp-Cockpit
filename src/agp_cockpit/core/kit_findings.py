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

AGP_KIT_CATALOG_GROUP_V1 (workflow-friction plan C5): the register lists only findings a Cockpit slice
entered; the Kit's own catalog has more (KIT-GF-090, 096-098, 100-120 at Kit 1.4.0). The installed Kit
answers ``greenfield status --json`` (K9: id, title, Kit state and fixed in per finding). Entries whose id
the register does not list become a group of their own in the window. The Cockpit reads only these four
fields and the report name, judges nothing and never writes them into its register.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

REGISTER = Path("docs/validation/AGENTIC_KIT_GREENFIELD_FINDINGS.json")
SEVERITY_ORDER = {"critical": 0, "major": 1, "high": 1, "medium-high": 2, "medium": 3, "low": 4}

OPEN = "offen"
IN_PROGRESS = "im Kit in Arbeit"
FIXED_NOT_INSTALLED = "behoben, nicht installiert"
FIXED_UNVERIFIED = "behoben, nicht bestätigt"
VERIFIED = "bestätigt behoben"
NOT_APPLICABLE = "laut Kit nicht anwendbar"

REGISTER_ORIGIN = "register"
KIT_CATALOG = "kit_catalog"                     # AGP_KIT_CATALOG_GROUP_V1
CATALOG_TIMEOUT = 120


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
    origin: str = REGISTER_ORIGIN               # AGP_KIT_CATALOG_GROUP_V1: register or Kit catalog

    def effective_status(self, installed: str | None) -> str:
        if self.status == "VERIFIED_FIXED":
            return VERIFIED
        fixed_in = self.fixed_in
        fixed = self.status == "FIXED" or bool(fixed_in)
        if not fixed and self.kit.get("kit_state") == "CLOSED" and not self._kit_closure_refuted():
            fixed, fixed_in = True, str(self.kit.get("fixed_in") or "")
        if fixed:
            # AGP_UNRELEASED_FIX_NOT_INSTALLED_V1 (2026-11-01, KIT-GF-094/095): the Kit catalog says
            # fixed_in "unreleased" for a fix on Kit main; "unreleased" parsed as version 0 and every
            # installed Kit counted as containing the fix. Only a release number can be installed.
            if installed and _is_release(fixed_in) and _version(installed) >= _version(fixed_in):
                return FIXED_UNVERIFIED
            return FIXED_NOT_INSTALLED
        if self.kit.get("kit_state") == "PARTIAL":
            return IN_PROGRESS
        if self.kit.get("kit_state") == "NOT_APPLICABLE":
            return NOT_APPLICABLE
        return OPEN

    def _kit_closure_refuted(self) -> bool:
        """The Cockpit reproduced the defect in a Kit at least as new as the Kit's claimed fix."""
        if not self.reproduced_in:
            return False
        kit_fixed = str(self.kit.get("fixed_in") or "")
        return not kit_fixed or _version(kit_fixed) <= _version(self.reproduced_in)

    def detail_text(self, installed: str | None) -> str:
        if self.origin == KIT_CATALOG:
            return self._catalog_text(installed)
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

    def _catalog_text(self, installed: str | None) -> str:
        fixed_in = str(self.kit.get("fixed_in") or "")
        lines = [f"{self.id} — {self.title or '(ohne Titel)'}", "",
                 f"Status: {self.effective_status(installed)} (Kit-Katalog: {self.kit.get('kit_state') or '?'}"
                 + (f", behoben in {fixed_in}" if fixed_in else "") + ")",
                 "", ("Nur im Kit-Katalog: Das Register des Cockpits führt diesen Befund nicht. Kennung, Titel, "
                      "Zustand und „behoben in“ sind die Angaben des installierten Kits (agentic-kit greenfield "
                      "status); das Cockpit bewertet sie nicht und trägt sie nicht ins Register ein.")]
        if self.kit.get("report"):
            lines += ["", f"Bericht im Kit-Repo: {self.kit['report']}"]
        return "\n".join(lines)


@dataclass(frozen=True)
class KitCatalog:
    """The installed Kit's answer to ``greenfield status --json``, reduced to what the window shows."""
    entries: tuple[dict, ...] = ()
    reason: str = ""                            # why there is no catalog (no Kit, no answer)


def catalog_argv(binary: Path | str) -> list[str]:
    return [str(binary), "greenfield", "status", "--json"]


def read_catalog(root: Path, runner: Callable = subprocess.run) -> KitCatalog:
    """Ask the repository's installed Kit for its finding catalog; never fails, a reason instead."""
    from agp_cockpit.core.kit_installation import discover
    root = Path(root)
    kit = discover(root)
    if kit is None:
        return KitCatalog(reason="kein Kit installiert")
    try:
        done = runner(catalog_argv(kit.binary), cwd=str(root), capture_output=True, text=True,
                      timeout=CATALOG_TIMEOUT, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return KitCatalog(reason=f"das Kit antwortet nicht ({type(exc).__name__})")
    text = f"{getattr(done, 'stdout', '') or ''}"
    try:
        data = json.loads(text[text.index("{"):])
    except ValueError:
        data = None
    findings = data.get("findings") if isinstance(data, dict) else None
    if not isinstance(findings, list):
        detail = str(data.get("error") or "") if isinstance(data, dict) else ""
        detail = detail or next((line.strip() for line in f"{getattr(done, 'stderr', '') or ''}".splitlines()
                                 if line.strip()), "")
        return KitCatalog(reason="greenfield status lieferte keinen Katalog" + (f": {detail}" if detail else ""))
    entries, seen = [], set()
    for item in findings:
        finding_id = str(item.get("id") or "").strip() if isinstance(item, dict) else ""
        if not finding_id or finding_id in seen:
            continue
        seen.add(finding_id)
        entries.append({"id": finding_id, "title": str(item.get("title") or ""),
                        "kit_state": str(item.get("kit_state") or ""), "fixed_in": str(item.get("fixed_in") or ""),
                        "report": str(item.get("report") or "")})
    return KitCatalog(entries=tuple(entries))


def catalog_only(register: list[KitFinding], catalog: KitCatalog | None) -> list[KitFinding]:
    """Catalog entries whose id the register does not list; the register always wins."""
    known = {finding.id for finding in register}
    return [KitFinding(id=entry["id"], title=entry["title"], severity="", status="", first_observed="",
                       kit={"kit_state": entry["kit_state"], "fixed_in": entry["fixed_in"], "report": entry["report"]},
                       origin=KIT_CATALOG)
            for entry in (catalog.entries if catalog else ()) if entry["id"] not in known]


def catalog_summary(extra: list[KitFinding], catalog: KitCatalog | None) -> str:
    if catalog is None:
        return "Kit-Katalog wird gelesen …"
    if catalog.reason:
        return f"Kit-Katalog nicht gelesen: {catalog.reason}"
    if not extra:
        return f"Kit-Katalog: {len(catalog.entries)} Einträge, alle auch im Register"
    return (f"Kit-Katalog: {len(extra)} von {len(catalog.entries)} Einträgen fehlen im Register "
            "(eigene Gruppe „Nur im Kit-Katalog“)")


def _text(value) -> str:
    if isinstance(value, list):
        return "\n".join(f"  · {_text(v)}" for v in value)
    if isinstance(value, dict):
        return "; ".join(f"{k}: {v}" for k, v in value.items())
    return str(value)


def _is_release(text: str | None) -> bool:
    return bool(re.fullmatch(r"\d+(\.\d+){1,3}(\.post\d+)?", str(text or "").strip()))


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


# AGP_FINDINGS_SORT_V1 (owner 2026-10-07): the table sorts by a clicked column; it opens
# sorted by ID. IDs sort by their number (KIT-GF-2 before KIT-GF-10), IDs without one last;
# severities by weight, not alphabetically.
SEVERITY_RANK = {"critical": 0, "major": 1, "high": 1, "medium-high": 2, "medium": 3, "low": 4}
SORT_COLUMNS = ("id", "title", "severity", "status", "first")


def sort_key(finding: KitFinding, column: str, installed: str | None = None) -> tuple:
    if column == "id":
        match = re.match(r"^KIT-GF-(\d+)$", finding.id)
        return (0, int(match.group(1)), "") if match else (1, 0, finding.id)
    if column == "title":
        return (finding.title.casefold(), finding.id)
    if column == "severity":
        return (SEVERITY_RANK.get(str(finding.severity).strip().lower(), 9), finding.id)
    if column == "status":
        return (finding.effective_status(installed), finding.id)
    if column == "first":
        return (str(finding.first_observed or ""), finding.id)
    raise ValueError(f"unknown column {column}")
