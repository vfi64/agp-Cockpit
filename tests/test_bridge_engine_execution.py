from types import SimpleNamespace

import agp_cockpit.core.bridge_engine as module
from agp_cockpit.core.bridge_execution import ExecutedBridgeStep
from agp_cockpit.core.bridge_protocol import BrowserTurnRequest
from agp_cockpit.core.mission_state import MissionStore


def _mission(tmp_path, *, mode="FULL_AUTO"):
    MissionStore(tmp_path).create(
        title="test",
        mission_text="test bridge execution",
        execution_mode="LIVE",
        run_mode=mode,
    )


def fake_step(tmp_path, *, rc=0, kind="generic"):
    order = SimpleNamespace(
        argv=("agentic-kit", "check")
        if kind == "kit"
        else ("/usr/bin/printf", "x"),
        cwd=tmp_path,
        kind=kind,
        label="demo",
    )
    return ExecutedBridgeStep(
        order=order,
        preview_text="preview",
        result_block="RESULT_BLOCK",
        returncode=rc,
        timed_out=False,
        stdout="stdout",
        stderr="stderr",
    )


def request(tmp_path):
    return BrowserTurnRequest(
        conversation_url="https://chatgpt.com/c/x",
        assistant_text=(
            '{"kind":"generic","cwd":"'
            + str(tmp_path)
            + '","argv":["/usr/bin/printf","x"],"label":"demo"}'
        ),
        turn_id="1",
    )


def test_success_executes_and_continues(monkeypatch, tmp_path):
    _mission(tmp_path)

    monkeypatch.setattr(
        module,
        "execute_structured_work_order",
        lambda *args, **kwargs: fake_step(tmp_path),
    )

    engine = module.BridgeEngine(tmp_path)
    response = engine.handle_turn(request(tmp_path))

    assert response.action == "continue"
    assert response.state == "STEP_PASS"
    assert "RESULT_BLOCK" in response.prompt


def test_done_stops_without_execution(monkeypatch, tmp_path):
    _mission(tmp_path)

    called = []
    monkeypatch.setattr(
        module,
        "execute_structured_work_order",
        lambda *args, **kwargs: called.append(True),
    )

    engine = module.BridgeEngine(tmp_path)
    response = engine.handle_turn(
        BrowserTurnRequest(
            conversation_url="https://chatgpt.com/c/x",
            assistant_text='{"mission_state":"DONE","summary":"finished"}',
            turn_id="1",
        )
    )

    assert response.action == "stop"
    assert response.state == "DONE"
    assert called == []
