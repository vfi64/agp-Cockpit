from agp_cockpit.core.mission_control import parse_mission_signal


def test_done_signal():
    signal = parse_mission_signal(
        '{"mission_state":"DONE","summary":"all green"}'
    )
    assert signal is not None
    assert signal.state == "DONE"


def test_work_order_is_not_signal():
    assert parse_mission_signal(
        '{"kind":"generic","cwd":"/tmp","argv":["echo","x"]}'
    ) is None
