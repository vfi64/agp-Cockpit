"""One traffic light for the active repository (AGP_AMPEL_V1, owner 2026-10-05).

The Lagebericht lists facts; the owner wants to see at a glance whether everything
is fine (green), something is open or waiting for him (yellow) or something is
wrong and needs him (red). The light is derived, never stored: from the repository
state (``repo_state``), the start guard (stale app, missing Kit), the outcome of the
last task this panel started, a pending decision and an offered recovery. Colour is
never the only signal: every light carries a word and a short German reason.
"""

from __future__ import annotations

from dataclasses import dataclass

from agp_cockpit.core import repo_state as rs

GRUEN = "GRÜN"
GELB = "GELB"
ROT = "ROT"
GRAU = "GRAU"

COLORS = {GRUEN: "#2e9d4b", GELB: "#d0a000", ROT: "#d03030", GRAU: "#888888"}


@dataclass(frozen=True)
class Ampel:
    color: str
    reason: str

    @property
    def hex(self) -> str:
        return COLORS[self.color]

    @property
    def text(self) -> str:
        return f"{self.color.capitalize()} — {self.reason}"


def ampel(state, *, block_reason: str = "", task_outcome: str = "", decision_pending: bool = False,
          recover_offered: bool = False, lage_error: str = "") -> Ampel:
    """Pure: the most urgent signal wins (red before yellow before green)."""
    if lage_error:
        return Ampel(ROT, "Lagebericht fehlgeschlagen")
    if block_reason:
        return Ampel(ROT, "Tasks gesperrt — " + _first_sentence(block_reason.removeprefix("Blockiert — ")))
    if decision_pending:
        return Ampel(GELB, "deine Entscheidung ist gefragt")
    if state is None:
        return Ampel(GRAU, "Lage wird geprüft")
    name = state.state
    if recover_offered and name != rs.LAEUFT:
        return Ampel(ROT, "Abschluss unterbrochen — „Wiederherstellen“")
    if task_outcome == "HUMAN_REQUIRED" and name not in (rs.BEREIT, rs.LAEUFT):
        return Ampel(ROT, "der letzte Task braucht dich")
    if name == rs.LAEUFT:
        return Ampel(GELB, "ein Task läuft")
    if name == rs.STOERUNG:
        if state.recommended == rs.ABSCHLIESSEN:
            return Ampel(GELB, "Post-Merge-Abschluss offen — „Abschließen“")
        return Ampel(ROT, "Störung — " + _first_sentence(state.summary))
    if name == rs.UNKLAR:
        return Ampel(ROT, "unklar — " + _first_sentence(state.summary))
    if name == rs.KEIN_KIT:
        return Ampel(GELB, "noch nicht unter Kit-Kontrolle")
    if name == rs.IN_ARBEIT:
        return Ampel(GELB, f"Arbeit auf {state.facts.branch or 'einem Branch'} offen")
    if name == rs.BEREIT:
        return Ampel(GRUEN, "alles in Ordnung, bereit für neue Arbeit")
    return Ampel(GRAU, name)


def _first_sentence(text: str, limit: int = 90) -> str:
    text = " ".join(str(text or "").split()).rstrip(".")
    head = text.split(". ")[0]
    return head if len(head) <= limit else head[:limit].rsplit(" ", 1)[0] + " …"
