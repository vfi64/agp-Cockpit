import inspect

from agp_cockpit.ui.mission_operator_panel import (
    MissionOperatorPanel,
)


def test_operator_panel_exists():
    assert inspect.isclass(MissionOperatorPanel)
