import pytest

from agp_cockpit.core.bridge_runtime import BridgeRuntime


def test_single_step_requires_explicit_resume(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(
        title="demo",
        mission_text="one step",
        execution_mode="LIVE",
        run_mode="SINGLE_STEP",
    )

    runtime.mark_running()
    state = runtime.record_step_result(
        result="ok",
        prompt="next",
        passed=True,
    )

    assert state.state == "WAITING_NEXT_STEP"

    state = runtime.resume_next_step()
    assert state.state == "RUNNING"


def test_resume_rejected_when_not_waiting(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(
        title="demo",
        mission_text="one step",
    )

    with pytest.raises(RuntimeError):
        runtime.resume_next_step()


def test_desktop_start_stops_nonterminal_previous_mission(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    created = runtime.create_mission(
        title="stale",
        mission_text="must not resume after app restart",
        execution_mode="LIVE",
        run_mode="FULL_AUTO",
    )

    state = runtime.stop_stale_on_desktop_start()

    assert state is not None
    assert state.mission_id == created.mission_id
    assert state.state == "STOPPED"
    assert "explicit restart required" in state.last_error
    assert runtime.state is None
    assert BridgeRuntime(tmp_path).state is None
    assert (runtime.store.root / f"{created.mission_id}.json").exists()
    assert not runtime.store.current_path.exists()


def test_desktop_start_preserves_terminal_mission(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(title="done", mission_text="already done")
    runtime.final("DONE", "complete")

    state = runtime.stop_stale_on_desktop_start()

    assert state is not None
    assert state.state == "DONE"
    assert state.last_summary == "complete"
    assert runtime.state is None
    assert not runtime.store.current_path.exists()


def test_runtime_can_persist_terminal_blocked_state(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(title="Task", mission_text="test")

    state = runtime.final("BLOCKED", "loop guard")

    assert state.state == "BLOCKED"
    assert runtime.store.load_current().state == "BLOCKED"


def test_runtime_stop_invokes_bound_execution_authority_before_persisting(tmp_path):
    events = []
    runtime = BridgeRuntime(tmp_path)
    runtime.create_mission(title="Task", mission_text="test")
    runtime.bind_execution_stop(
        lambda: events.append("process-stop") or {"requested": True}
    )

    state = runtime.stop("operator stop")

    assert state.state == "STOPPED"
    assert events == ["process-stop"]
    assert runtime.last_execution_stop == {"requested": True}
