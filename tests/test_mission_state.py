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


def test_canonical_state_transition_contract():
    from agp_cockpit.core.mission_state import validate_state_transition
    for previous_state, next_state in [
        ('READY', 'RUNNING'),
        ('RUNNING', 'RUNNING'),
        ('RUNNING', 'WAITING_NEXT_STEP'),
        ('WAITING_NEXT_STEP', 'RUNNING'),
        ('RUNNING', 'DONE'),
        ('RUNNING', 'FAILED'),
        ('RUNNING', 'NEEDS_HUMAN'),
        ('RUNNING', 'STOPPED'),
    ]:
        validate_state_transition(previous_state, next_state)


def test_canonical_state_transition_contract_rejects_illegal_edges():
    import pytest
    from agp_cockpit.core.mission_state import validate_state_transition
    for next_state in ('DONE', 'FAILED', 'NEEDS_HUMAN'):
        validate_state_transition('READY', next_state)
    with pytest.raises(ValueError, match='READY -> STOPPED'):
        validate_state_transition('READY', 'STOPPED')
    with pytest.raises(ValueError, match='DONE -> RUNNING'):
        validate_state_transition('DONE', 'RUNNING')
