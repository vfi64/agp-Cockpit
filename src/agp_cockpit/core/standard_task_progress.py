"""Operator-facing progress text for a started Standard Task.

AGP_STANDARD_TASK_PROGRESS_V1
Live 2026-09-30: the Standard Tasks panel set its status line once at start
("WAITING_FOR_REMOTE") and never refreshed it, although the mission reached
DONE and the durable task VERIFIED_COMPLETE. The panel now polls and derives
its text from both authorities: the bridge mission state (bound to the started
mission id) and the durable task state (bound to the started task id).
"""

from __future__ import annotations

from dataclasses import dataclass

MISSION_TERMINAL = frozenset({"DONE", "FAILED", "NEEDS_HUMAN", "BLOCKED", "STOPPED"})
HUMAN_REQUIRED = frozenset({"NEEDS_HUMAN", "BLOCKED", "FAILED"})


@dataclass(frozen=True)
class StandardTaskProgress:
    text: str
    terminal: bool
    outcome: str  # RUNNING | DONE | HUMAN_REQUIRED | STOPPED | UNKNOWN


def _reason(mission: dict) -> str:
    for key in ("last_error", "browser_transport_block_reason", "last_summary", "last_result"):
        value = " ".join(str(mission.get(key) or "").split())
        if value:
            return value[:240]
    return ""


def describe_standard_task_progress(
    *, mission_id: str, task_status: dict | None, bridge_status: dict | None
) -> StandardTaskProgress:
    task_state = str((task_status or {}).get("state") or "")
    suspension = str((task_status or {}).get("suspension_reason") or "")
    mission = (bridge_status or {}).get("mission") if bridge_status else None
    local = f"Lokaler Task: {task_state or 'unbekannt'}"

    if not isinstance(mission, dict) or str(mission.get("mission_id") or "") != mission_id:
        if task_state == "VERIFIED_COMPLETE":
            return StandardTaskProgress(
                f"Fertig ✓ — lokaler Task verifiziert. Die Bridge zeigt diese Mission nicht mehr an. {local}",
                True, "DONE")
        return StandardTaskProgress(
            f"Unklar — die Bridge zeigt die gestartete Mission nicht (mehr) an. {local}",
            False, "UNKNOWN")

    mstate = str(mission.get("state") or "")
    turns = int(mission.get("turn_count") or 0)
    steps = int(mission.get("step_count") or 0)
    counters = f"{turns} Remote-Turns · {steps} Schritte"
    reason = _reason(mission)
    suffix = f" — {reason}" if reason else ""

    if suspension == "WAITING_FOR_HUMAN":
        return StandardTaskProgress(
            f"Mensch muss eingreifen — Entscheidung erforderlich. Mission: {mstate} · {local}",
            False, "HUMAN_REQUIRED")
    if mstate == "DONE":
        if task_state == "VERIFIED_COMPLETE":
            return StandardTaskProgress(
                f"Fertig ✓ — Ergebnis lokal verifiziert und übergeben ({counters}). "
                f"Mission: DONE · {local}",
                True, "DONE")
        # Mission and durable task disagree: never report success silently.
        return StandardTaskProgress(
            f"Mensch muss prüfen — Mission meldet DONE, lokaler Task ist nicht verifiziert. {local}",
            True, "HUMAN_REQUIRED")
    if mstate in HUMAN_REQUIRED:
        return StandardTaskProgress(
            f"Mensch muss eingreifen — Mission: {mstate}{suffix} · {local}", True, "HUMAN_REQUIRED")
    if mstate == "STOPPED" or task_state == "CANCELLED":
        return StandardTaskProgress(
            f"Gestoppt — Mission: {mstate}{suffix} · {local}", True, "STOPPED")
    if turns == 0 and steps == 0:
        return StandardTaskProgress(
            f"Gestartet — wartet auf die erste Remote-Antwort. Mission: {mstate} · {local}",
            False, "RUNNING")
    return StandardTaskProgress(
        f"Läuft — {counters}. Mission: {mstate} · {local}", False, "RUNNING")
