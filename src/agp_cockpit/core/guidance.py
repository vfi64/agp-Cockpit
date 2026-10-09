"""Lösungsweg: numbered next steps for the owner (AGP_GUIDED_RECOVERY_V1, owner 2026-10-06).

Live 2026-10-05/06 (PR #242/#243): GitHub gave a CI job no runner, the Kit's follow-up
step timed out, its fallback crashed and left a leftover branch. The traffic light was
right, but the way out (re-run on GitHub, „Wiederherstellen“, approve, back to main,
„Abschließen“) came from the chat, not from the Cockpit. The Cockpit now derives the
steps itself, pure and from what it already knows: repository state, follow-up pull
request CI, pending decision, offered recovery, stale app, last task outcome. At most
three short steps; the first one is the next action.
"""

from __future__ import annotations

from agp_cockpit.core import repo_state as rs

MAX_STEPS = 3


def steps(state, *, block_reason: str = "", decision_pending: bool = False, recover_offered: bool = False,
          task_outcome: str = "", repository: str = "") -> list[str]:
    if block_reason:
        if "Build" in block_reason or "App" in block_reason:
            return ["Oben rechts „Neu bauen und neu starten“ bzw. „Neu starten“ klicken.",
                    "Danach geht es hier weiter."]
        return [block_reason.removeprefix("Blockiert — "), "Danach „Aktualisieren“ klicken."]
    if decision_pending:
        return ["Im Kasten „Deine Entscheidung ist gefragt“ die Frage lesen.",
                "„Freigeben“ nur, wenn der Eingriff genau das Genannte betrifft; sonst „Ablehnen“."]
    if state is None:
        return []
    f = state.facts
    name = state.state
    if name == rs.LAEUFT:
        return ["Nichts tun — ein Task läuft; den Fortschritt zeigt die Zeile unten."]
    if recover_offered:
        return ["„Wiederherstellen“ klicken: Diagnose zuerst, Eingriffe nur nach deiner Freigabe.",
                "Dem Lösungsweg danach weiter folgen."]
    if name == rs.STOERUNG and state.recommended == rs.ABSCHLIESSEN:
        return _followup_steps(f)
    if name == rs.STOERUNG:
        return ["„Wiederherstellen“ klicken: Diagnose zuerst, Eingriffe nur nach deiner Freigabe.",
                "Dem Lösungsweg danach weiter folgen."]
    if name == rs.UNKLAR:
        first = state.reasons[0] if state.reasons else state.summary
        return [f"Ursache beheben: {first}", "Danach „Aktualisieren“ klicken."]
    if name == rs.KEIN_KIT:
        return ["Das Repo zuerst unter Kit-Kontrolle bringen („Repo übernehmen“, folgt mit P9)."]
    if name == rs.IN_ARBEIT:
        if not f.own_commits and not f.changes and f.head and f.head == f.origin_main:
            # AGP_FRESH_BRANCH_V1 (live 2026-10-06): right after „Arbeit beginnen“ an empty work
            # branch is expected; only a Kit follow-up branch (docs/post-pr<N>-…) is a leftover.
            if not rs.FOLLOWUP_BRANCH.match(f.branch or ""):
                return [f"Branch {f.branch} ist bereit — „Arbeiten“ für den Auftrag, danach „Abschließen“."]
            where = f"cd {repository} && " if repository else ""
            return [f"Der Branch {f.branch} enthält keine Arbeit (Rest eines Ablaufs).",
                    f"Zurück auf main: {where}git switch main",
                    "Danach „Aktualisieren“ klicken."]
        if f.own_commits and not f.changes:
            return ["„Abschließen“ klicken: Commit ist da; veröffentlicht, prüft die CI und mergt."]
        if task_outcome == "HUMAN_REQUIRED":
            return ["Die letzte Meldung unten lesen.",
                    "Reparierbar mit „Arbeiten“ (Auftrag beschreiben) oder „Wiederherstellen“."]
        if state.recommended == rs.ABSCHLIESSEN:
            return ["„Abschließen“ klicken: committet, veröffentlicht, prüft die CI und mergt."]
        return ["„Arbeiten“ für den nächsten Auftrag, danach „Abschließen“."]
    if name == rs.BEREIT:
        return []
    return []


def _followup_steps(f) -> list[str]:
    pr = f"PR #{f.followup_pr}" if f.followup_pr else "der Folge-PR"
    url = f" ({f.followup_url})" if f.followup_url else ""
    if f.followup_ci == rs.FOLLOWUP_RUNNER:
        return [f"Auf GitHub {pr}{url}: „Re-run failed jobs“ — GitHub hat einen CI-Job ohne Runner abgebrochen.",
                "Warten, bis die CI grün ist, dann „Aktualisieren“.",
                "Dann „Abschließen“ klicken."]
    if f.followup_ci == rs.FOLLOWUP_NOT_STARTED:
        return [f"GitHub hat die CI von {pr}{url} nicht gestartet (oft: Actions-Kontingent oder Billing).",
                "Auf GitHub die Laufseite öffnen, den Grund prüfen und „Re-run all jobs“ klicken.",
                "Wenn die CI grün ist: „Aktualisieren“, dann „Abschließen“."]
    if f.followup_ci == rs.FOLLOWUP_PENDING:
        return [f"Warten: die CI von {pr} läuft noch (GitHub).", "Dann „Aktualisieren“ und „Abschließen“."]
    if f.followup_ci == rs.FOLLOWUP_FAILED:
        return [f"Die CI von {pr} ist rot (echter Fehler){url}.",
                "„Wiederherstellen“ klicken: Diagnose, Reparatur nur nach Freigabe."]
    return [f"„Abschließen“ klicken: bringt {pr} des Kits zu Ende (CI {'grün' if f.followup_ci else 'wird geprüft'})."]


def text(items: list[str]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(items[:MAX_STEPS], 1))
