"""Lifecycle verbs of the Standard Tasks tab — one text table (plan P3).

AGP_STANDARD_TASK_VERBS_V1: label, place in the UI, effect badge and the three
tooltip lines (what happens · effect · when available) live here only; the UI
and the documentation read them from this table so they cannot drift apart.
``slice`` names the plan slice that still has to implement a verb; such a
verb is shown but disabled ("in Vorbereitung"). ``kit_gate`` names the open
Kit findings a verb waits for (AGP_KIT_GATED_VERBS_V1, owner 2026-10-02: the
Cockpit steers, the remote LLM decides, the Kit controls — a verb without a
Kit route waits for the Kit instead of a Cockpit-local workaround).
"""

from __future__ import annotations

from dataclasses import dataclass

from agp_cockpit.core import repo_state as rs

LIEST = "liest nur"
LOKAL = "ändert lokal"
GITHUB = "wirkt auf GitHub"
FRAGT = "fragt vor Eingriffen"
JE_NACH = "je nach Auftrag"


@dataclass(frozen=True)
class Verb:
    key: str
    label: str
    group: str            # weg | probleme | weitere
    step: int | None      # position on the main path (1..4)
    badge: str
    what: str
    effect: str
    when: str
    task_key: str | None = None   # StandardTask key when implemented as a task
    slice: str | None = None      # plan slice when not yet implemented
    kit_gate: str | None = None   # open Kit findings the verb waits for

    def tooltip(self) -> str:
        return f"{self.what}\nWirkung: {self.effect}\nVerfügbar: {self.when}"


VERBS: tuple[Verb, ...] = (
    Verb(rs.ARBEIT_BEGINNEN, "Arbeit beginnen", "weg", 1, LOKAL,
         "Synchronisiert main, bestätigt die Kit-Regeln und legt einen neuen Arbeitsbranch an.",
         "liest origin; der Start gibt genau die Synchronisierung und das Anlegen des Branches über das Kit frei.",
         "wenn main synchron und sauber ist (Zustand BEREIT).", task_key="work-start"),
    Verb(rs.ARBEITEN, "Arbeiten", "weg", 2, JE_NACH,
         "Öffnet den Tab „Arbeiten“ für einen frei formulierten Auftrag an die Remote-LLM.",
         "hängt vom Auftrag ab; Wirkung nach außen nur mit Freigabe.",
         "auf einem Arbeitsbranch (Zustand IN_ARBEIT)."),
    Verb(rs.ABSCHLIESSEN, "Abschließen", "weg", 3, GITHUB,
         "Veröffentlicht die Arbeit: Commit, Push, Pull Request, grüne CI, Merge und Post-Merge-Abschluss "
         "des Kits. Fertig erst, wenn das Cockpit GitHub selbst grün geprüft hat.",
         "pusht und mergt nach main (der Start ist die Freigabe; nie von main, kein Force-Push).",
         "auf einem Arbeitsbranch mit eigenen Commits (Zustand IN_ARBEIT).", task_key="finish"),
    Verb(rs.CHAT_WECHSELN, "Chat wechseln", "weg", 4, LOKAL,
         "Erzeugt und prüft das Übergabepaket für einen neuen Chat; öffnet selbst keinen neuen Chat.",
         "schreibt nur die Übergabedateien im Repo.",
         "in jedem ruhenden Zustand außer UNKLAR und KEIN_KIT.", task_key="chat-switch"),
    Verb(rs.WIEDERHERSTELLEN, "Wiederherstellen", "probleme", None, FRAGT,
         "Grundversion: Diagnose über die Remote-LLM und Reparatur nur über Kit-Befehle; wo das Kit "
         "keinen Weg hat (Änderungen oder Commits auf main, KIT-GF-033), fragt es dich. Die vollständige "
         "Version folgt nach dem Kit-Fix.",
         "erst nur lesend; zerstörerische Schritte nur nach deiner Freigabe.",
         "bei einer Störung (Zustand STÖRUNG) oder nach einem abgebrochenen Abschließen.",
         task_key="recover"),
    Verb(rs.REPO_UEBERNEHMEN, "Repo übernehmen", "weitere", None, LOKAL,
         "Analysiert ein fremdes Repo und legt die Kit-Steuerschicht an.",
         "ändert lokal; ein neues GitHub-Repo nur nach Freigabe.",
         "wenn das Repo noch nicht unter Kit-Kontrolle steht (Zustand KEIN_KIT).", slice="P9"),
    Verb(rs.RELEASE, "Release", "weitere", None, FRAGT,
         "Prüft und veröffentlicht eine Version über das Kit.",
         "wirkt auf GitHub; fragt immer.",
         "auf sauberem, synchronem main (Zustand BEREIT).", slice="P11",
         kit_gate="KIT-GF-029, KIT-GF-032"),
    Verb(rs.PFLEGE, "Pflege", "weitere", None, LOKAL,
         "Räumt Kit-Übertragungsreste auf, prüft Dokumente auf Aktualität, hebt die Kit-Steuerschicht "
         "und das Kit selbst auf den neuesten Stand.",
         "ändert lokal; Ergebnisse gehen über „Abschließen“ ins Repo.",
         "auf sauberem, synchronem main (Zustand BEREIT).", slice="P10"),
)
BY_KEY = {verb.key: verb for verb in VERBS}


def availability(verb: Verb, state: rs.RepoState | None, *,
                 recover_offered: bool = False) -> tuple[bool, str]:
    """(enabled, reason shown when disabled). ``recover_offered``: an
    interrupted Abschließen unlocks Wiederherstellen (R6) unless a task runs."""
    if verb.kit_gate is not None:
        return False, f"Wartet auf einen Kit-Fix ({verb.kit_gate}); bis dahin von Hand."
    if verb.slice is not None:
        return False, f"In Vorbereitung (Plan {verb.slice})."
    if state is None:
        return False, "Lagebericht läuft noch."
    if recover_offered and verb.key == rs.WIEDERHERSTELLEN and state.state != rs.LAEUFT:
        return True, ""
    if verb.key not in state.offered:
        return False, f"Jetzt nicht verfügbar — {verb.when} Aktuell: {state.state}, {state.summary}"
    return True, ""
