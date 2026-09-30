from pathlib import Path

from agp_cockpit.core.standard_task_progress import describe_standard_task_progress

ROOT = Path(__file__).resolve().parents[1]
PANEL = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
MID = "ab040cc1-0046-454e-a77a-0095a914ff24"


def bridge(state, mission_id=MID, turns=1, steps=1, **extra):
    return {"state": state, "mission": {"mission_id": mission_id, "state": state,
                                        "turn_count": turns, "step_count": steps, **extra}}


def progress(task_state, bridge_payload, suspension=None):
    return describe_standard_task_progress(
        mission_id=MID,
        task_status={"state": task_state, "suspension_reason": suspension},
        bridge_status=bridge_payload,
    )


def test_live_2026_09_30_done_and_verified_is_reported_as_finished():
    result = progress("VERIFIED_COMPLETE", bridge("DONE"))
    assert result.outcome == "DONE" and result.terminal
    assert result.text.startswith("Fertig ✓")
    assert "WAITING_FOR_REMOTE" not in result.text


def test_mission_done_without_verified_task_is_not_success():
    result = progress("WAITING_FOR_REMOTE", bridge("DONE"))
    assert result.outcome == "HUMAN_REQUIRED" and result.terminal
    assert "nicht verifiziert" in result.text


def test_needs_human_and_blocked_surface_reason():
    result = progress("WAITING_FOR_REMOTE", bridge("BLOCKED", last_error="unresolved in-flight step"))
    assert result.outcome == "HUMAN_REQUIRED" and result.terminal
    assert "unresolved in-flight step" in result.text
    assert progress("WAITING_FOR_REMOTE", bridge("NEEDS_HUMAN")).outcome == "HUMAN_REQUIRED"


def test_waiting_for_human_checkpoint_keeps_polling():
    result = progress("SUSPENDED", bridge("RUNNING"), suspension="WAITING_FOR_HUMAN")
    assert result.outcome == "HUMAN_REQUIRED" and not result.terminal


def test_running_mission_keeps_polling_with_counters():
    result = progress("WAITING_FOR_REMOTE", bridge("RUNNING", turns=2, steps=1))
    assert result.outcome == "RUNNING" and not result.terminal
    assert "2 Remote-Turns" in result.text
    assert progress("WAITING_FOR_REMOTE", bridge("RUNNING", turns=0, steps=0)).text.startswith("Gestartet")


def test_foreign_mission_is_never_reported_as_this_task():
    result = progress("WAITING_FOR_REMOTE", bridge("DONE", mission_id="other"))
    assert result.outcome == "UNKNOWN" and not result.terminal
    assert progress("WAITING_FOR_REMOTE", None).outcome == "UNKNOWN"


def test_stopped_is_terminal():
    assert progress("CANCELLED", bridge("STOPPED")).outcome == "STOPPED"


def test_panel_polls_progress_after_start():
    assert "describe_standard_task_progress" in PANEL
    assert "self._track(str(mission[\"mission_id\"]))" in PANEL
    assert "after_cancel" in PANEL
