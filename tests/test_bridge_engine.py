from types import SimpleNamespace

import agp_cockpit.core.bridge_engine as module
from agp_cockpit.core.bridge_engine import BridgeEngine
from agp_cockpit.core.bridge_protocol import BrowserTurnRequest
from agp_cockpit.core.mission_state import MissionStore


def _create_live_full_auto_mission(tmp_path):
    MissionStore(tmp_path).create(
        title="test mission",
        mission_text="test one bridge turn",
        execution_mode="LIVE",
        run_mode="FULL_AUTO",
    )


def test_structured_step_continues(monkeypatch, tmp_path):
    _create_live_full_auto_mission(tmp_path)

    fake_order = SimpleNamespace(
        argv=("/usr/bin/printf", "x"),
        cwd=tmp_path,
        kind="generic",
        label="demo",
    )
    fake_step = module.ExecutedBridgeStep(
        order=fake_order,
        preview_text="preview",
        result_block="RESULT",
        returncode=0,
        timed_out=False,
        stdout="x",
        stderr="",
    )

    monkeypatch.setattr(
        module,
        "execute_structured_work_order",
        lambda *args, **kwargs: fake_step,
    )

    engine = BridgeEngine(tmp_path)
    response = engine.handle_turn(
        BrowserTurnRequest(
            conversation_url="https://chatgpt.com/c/x",
            assistant_text=(
                '{"kind":"generic","cwd":"'
                + str(tmp_path)
                + '","argv":["/usr/bin/printf","x"],'
                '"timeout_seconds":5,"label":"demo"}'
            ),
            turn_id="1",
        )
    )

    assert response.action == "continue"
    assert response.state == "STEP_PASS"


def test_unstructured_step_stops(tmp_path):
    _create_live_full_auto_mission(tmp_path)

    engine = BridgeEngine(tmp_path)
    response = engine.handle_turn(
        BrowserTurnRequest(
            conversation_url="https://chatgpt.com/c/x",
            assistant_text="Just prose",
            turn_id="1",
        )
    )

    assert response.action == "stop"
