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
