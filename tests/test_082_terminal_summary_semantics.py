from __future__ import annotations

from agp_cockpit.core.bridge_runtime import BridgeRuntime
from agp_cockpit.core.mission_state import MissionState


def _runtime(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(
        title="terminal semantics",
        mission_text="bounded test",
        execution_mode="LIVE",
        run_mode="FULL_AUTO",
    )
    return runtime


def test_done_note_is_summary_not_error(tmp_path):
    runtime = _runtime(tmp_path)
    state = runtime.final("DONE", "completed successfully")
    assert state.state == "DONE"
    assert state.last_summary == "completed successfully"
    assert state.last_error == ""


def test_needs_human_note_is_summary_not_error(tmp_path):
    runtime = _runtime(tmp_path)
    state = runtime.final("NEEDS_HUMAN", "choose target")
    assert state.last_summary == "choose target"
    assert state.last_error == ""


def test_failed_note_remains_error(tmp_path):
    runtime = _runtime(tmp_path)
    state = runtime.final("FAILED", "boom")
    assert state.last_summary == ""
    assert state.last_error == "boom"


def test_old_persisted_mission_without_last_summary_remains_loadable(tmp_path):
    state = MissionState(
        repository_root=str(tmp_path),
        title="old",
        mission_text="old",
        state="DONE",
    )
    data = state.to_dict()
    data.pop("last_summary")
    loaded = MissionState.from_dict(data)
    assert loaded.state == "DONE"
    assert loaded.last_summary == ""
