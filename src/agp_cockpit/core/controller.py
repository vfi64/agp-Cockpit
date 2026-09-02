from __future__ import annotations

from .models import CockpitSession, RunState


class CockpitController:
    """Application coordinator.

    The controller transports work; it does not replace Agentic Project
    Kit workflow decisions.
    """

    def __init__(self, session: CockpitSession) -> None:
        self.session = session

    @property
    def state(self) -> RunState:
        return self.session.state
