from agp_cockpit.core.mission_state import MissionStore


def test_create_save_resume(tmp_path):
    store = MissionStore(tmp_path)
    state = store.create(
        title="demo",
        mission_text="do one thing",
        execution_mode="DRY_RUN",
        run_mode="SINGLE_STEP",
    )

    loaded = store.load_current()
    assert loaded is not None
    assert loaded.mission_id == state.mission_id
    assert loaded.execution_mode == "DRY_RUN"
    assert loaded.run_mode == "SINGLE_STEP"
