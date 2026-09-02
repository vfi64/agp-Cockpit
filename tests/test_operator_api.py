from agp_cockpit.core.operator_api import OperatorAPI


def test_operator_create_status_resume(tmp_path):
    api = OperatorAPI(tmp_path)

    created = api.create(
        title="test",
        mission_text="one step",
        execution_mode="LIVE",
        run_mode="SINGLE_STEP",
    )
    assert created["state"] == "READY"

    runtime = api.runtime
    runtime.mark_running()
    runtime.record_step_result(
        result="ok",
        prompt="next",
        passed=True,
    )

    status = api.status()
    assert status["state"] == "WAITING_NEXT_STEP"

    resumed = api.resume_next_step()
    assert resumed["state"] == "RUNNING"
