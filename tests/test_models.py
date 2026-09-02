from agp_cockpit.core.models import CockpitSession, CommunicationMode, RunState


def test_new_session_is_idle() -> None:
    session = CockpitSession(
        repository="/tmp/example",
        mode=CommunicationMode.COPY_PASTE,
    )
    assert session.state is RunState.IDLE


def test_modes_are_stable_strings() -> None:
    assert CommunicationMode.COPY_PASTE.value == "copy_paste"
    assert CommunicationMode.FILE_TRANSFER.value == "file_transfer"
