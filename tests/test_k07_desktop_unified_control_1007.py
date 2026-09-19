from pathlib import Path

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
