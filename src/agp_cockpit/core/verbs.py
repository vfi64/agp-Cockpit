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
         "pusht und mergt nach main (der Start ist die Freigabe; von main nur, um den offenen "
         "Post-Merge-Abschluss des Kits zu Ende zu bringen; kein Force-Push).",
         "auf einem Arbeitsbranch mit eigenen Commits (Zustand IN_ARBEIT) oder auf main, wenn nur "
         "der Post-Merge-Abschluss des Kits offen ist.", task_key="finish"),
    Verb(rs.CHAT_WECHSELN, "Chat wechseln", "weg", 4, LOKAL,
         "Erzeugt und prüft das Übergabepaket für einen neuen Chat; öffnet selbst keinen neuen Chat.",
         "schreibt nur die Übergabedateien im Repo.",
         "in jedem ruhenden Zustand außer UNKLAR und KEIN_KIT.", task_key="chat-switch"),
    Verb(rs.WIEDERHERSTELLEN, "Wiederherstellen", "probleme", None, FRAGT,
         "Diagnose über die Remote-LLM, Reparatur nur über Kit-Befehle. Änderungen oder Commits auf "
         "main sichert das Kit erst auf einem Rescue-Branch, dann richtet es main neu aus (KIT-GF-033, "
         "behoben in Kit 1.0.14).",
         "erst nur lesend (Probelauf); jeder zerstörerische Schritt nur nach deiner Freigabe.",
         "bei einer Störung (Zustand STÖRUNG) oder nach einem abgebrochenen Abschließen.",
         task_key="recover"),
    Verb(rs.REPO_UEBERNEHMEN, "Repo übernehmen", "weitere", None, LOKAL,
         "Analysiert ein fremdes Repo und legt die Kit-Steuerschicht an.",
         "ändert lokal; ein neues GitHub-Repo nur nach Freigabe.",
         "wenn das Repo noch nicht unter Kit-Kontrolle steht (Zustand KEIN_KIT).", slice="P9"),
    Verb(rs.RELEASE, "Release", "weitere", None, FRAGT,
         "Privates Release über das Kit: Release-Branch mit Release-Vorbereitung, Merge bei grüner CI, "
         "dann das annotierte Tag (kein GitHub Release, kein PyPI, kein Zenodo).",
         "der Start gibt Release-Branch und Merge frei; der Tag-Push fragt immer mit der Signatur des Probelaufs.",
         "auf sauberem, synchronem main (Zustand BEREIT).", task_key="release"),
    Verb(rs.PFLEGE, "Pflege", "weitere", None, LOKAL,
         "Pflegt die Kit-Steuerschicht mit den Kit-Routen: Schema-Upgrade, Aufräumen von "
         "Übertragungsresten — erst als Probelauf; Dokument-Hinweise nur als Bericht. "
         "Das Kit-Update folgt mit P10b.",
         "ändert lokal; Ergebnisse gehen über „Abschließen“ ins Repo.",
         "auf sauberem, synchronem main (Zustand BEREIT).", task_key="maintain"),
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


def recover_not_needed(state) -> bool:
    """AGP_RECOVER_OFFER_EXPIRES_V1: a clean work branch with own commits, ready to be
    finished, needs no recovery (an interrupted publication is resumed by „Abschließen“)."""
    facts = getattr(state, "facts", None)
    if state is None or facts is None or getattr(state, "recommended", None) != rs.ABSCHLIESSEN:
        return False
    if getattr(state, "state", None) == rs.STOERUNG:
        # AGP_RECOVER_OFFER_EXPIRES_V2 (live 2026-10-09, PR #319): main is clean and synchronized and
        # only the Kit's follow-up pull request is open; unless its CI found a real failure,
        # „Abschließen“ completes it — „Wiederherstellen“ would end at the same step.
        return getattr(facts, "followup_ci", "") != rs.FOLLOWUP_FAILED
    return bool(getattr(state, "state", None) == rs.IN_ARBEIT and facts.own_commits and not facts.changes)
