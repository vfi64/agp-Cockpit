from pathlib import Path

from agp_cockpit.core.bridge_runtime import BridgeRuntime


def test_operator_stop_terminates_ready_mission_and_survives_reload(tmp_path: Path):
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(
        title="Standard · Chat wechseln",
        mission_text="handoff",
        execution_mode="LIVE",
        run_mode="FULL_AUTO",
    )

    stopped = runtime.stop("Stopped by operator control")

    assert stopped.state == "STOPPED"
    assert BridgeRuntime(tmp_path).require_state().state == "STOPPED"


def test_operator_stop_is_idempotent_for_terminal_mission(tmp_path: Path):
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(title="Task", mission_text="done")
    runtime.final("DONE", "complete")

    assert runtime.stop().state == "DONE"
