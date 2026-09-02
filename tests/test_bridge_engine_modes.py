import agp_cockpit.core.bridge_engine as module
from agp_cockpit.core.bridge_engine import BridgeEngine
from agp_cockpit.core.bridge_protocol import BrowserTurnRequest
from agp_cockpit.core.mission_state import MissionStore


def test_dry_run_does_not_execute(monkeypatch, tmp_path):
    store = MissionStore(tmp_path)
    store.create(
        title="dry",
        mission_text="preview",
        execution_mode="DRY_RUN",
        run_mode="SINGLE_STEP",
    )

    engine = BridgeEngine(tmp_path)

    monkeypatch.setattr(
        module,
        "preview_structured_work_order",
        lambda *a, **k: type(
            "Preview",
            (),
            {"preview_text": "SAFE PREVIEW"},
        )(),
    )

    called = []
    monkeypatch.setattr(
        module,
        "execute_structured_work_order",
        lambda *a, **k: called.append(True),
    )

    response = engine.handle_turn(
        BrowserTurnRequest(
            conversation_url="https://chatgpt.com/c/x",
            assistant_text=(
                '{"kind":"generic","cwd":"'
                + str(tmp_path)
                + '","argv":["/usr/bin/printf","x"],'
                '"label":"demo"}'
            ),
            turn_id="1",
        )
    )

    assert response.state == "DRY_RUN_PREVIEW"
    assert called == []


def test_missing_mission_stops(tmp_path):
    engine = BridgeEngine(tmp_path)

    response = engine.handle_turn(
        BrowserTurnRequest(
            conversation_url="https://chatgpt.com/c/x",
            assistant_text="anything",
            turn_id="1",
        )
    )

    assert response.action == "stop"
    assert response.state == "AUTOMATION_STOP"
