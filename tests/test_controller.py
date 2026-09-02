from agp_cockpit.core.controller import CockpitController
from agp_cockpit.core.models import CockpitSession, CommunicationMode, RunState


def test_controller_exposes_session_state() -> None:
    controller = CockpitController(
        CockpitSession("/tmp/example", CommunicationMode.FILE_TRANSFER)
    )
    assert controller.state is RunState.IDLE
