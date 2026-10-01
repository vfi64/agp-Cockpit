import json
from pathlib import Path

from agp_cockpit.adapters.macos_settings import bridge_runtime_root
from agp_cockpit.core.task_contract import LocalTaskContract
from agp_cockpit.core.task_operator_api import TaskOperatorAPI


def test_desktop_methods_publish_operator_control(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME",str(tmp_path))
    api=TaskOperatorAPI(tmp_path)
    before=api.file_loop_status()
    pause_snapshot=api.file_loop_pause()
    assert pause_snapshot == before
    assert api.operator_control.current()=={"generation":1,"action":"PAUSE"}
    api.file_loop_resume()
    assert api.operator_control.current()=={"generation":2,"action":"RESUME"}
    api.file_loop_stop()
    assert api.operator_control.current()=={"generation":3,"action":"STOP"}
    api.controller.close()


def test_new_task_clears_stale_stop_control(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    api = TaskOperatorAPI(
        tmp_path,
        local_contract=LocalTaskContract(
            tmp_path,
            allowed_effects=frozenset({"E2"}),
            allowed_tools=frozenset({"git", "agentic-kit"}),
        ),
    )
    api.file_loop_stop()

    api.start_task_from_contract(
        {
            "task_id": "fresh-task",
            "title": "Fresh task",
            "goal": "Start a new task after a previous stop.",
        }
    )

    assert api.operator_control.current()["action"] == "RESUME"
    api.controller.close()


def test_task_operator_uses_bridge_runtime_control_path(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    api = TaskOperatorAPI(tmp_path)

    api.file_loop_stop()

    bridge_control = bridge_runtime_root() / "operator-control.json"
    assert bridge_control.exists()
    assert json.loads(bridge_control.read_text())["action"] == "STOP"
    assert api.operator_control.path == bridge_control
    api.controller.close()
