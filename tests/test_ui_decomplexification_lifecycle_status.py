from pathlib import Path

from agp_cockpit.core.task_operator_api import TaskOperatorAPI


def test_visible_file_loop_status_tracks_shared_operator_control(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    api=TaskOperatorAPI(tmp_path)
    api.file_loop_pause(); assert api.file_loop_status()["state"]=="PAUSED"
    api.file_loop_resume(); assert api.file_loop_status()["state"]=="RUNNING"
    api.file_loop_stop(); assert api.file_loop_status()["state"]=="STOPPED"
    assert api.file_loop_status()["generation"]==3
    api.controller.close()
