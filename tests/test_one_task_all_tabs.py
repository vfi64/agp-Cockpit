"""AGP_ONE_TASK_ALL_TABS_V1 (R5): live 2026-10-04 the Arbeiten tab started a task while
„Arbeit beginnen“ was still running (missions 1729/1730); its mission replaced the running
one and the work-start order landed in the new task without scope."""

from pathlib import Path

from agp_cockpit.core import mission_http_client as client

ROOT = Path(__file__).resolve().parents[1]


def test_running_means_any_state_that_is_not_resting():
    for state in ("READY", "RUNNING", "WAITING", "ACTIVE"):
        assert client.mission_running({"state": state})
    for state in ("", "DONE", "NEEDS_HUMAN", "STOPPED", "FAILED"):
        assert not client.mission_running({"state": state})
    assert not client.mission_running({}) and not client.mission_running(None)


def test_unreachable_bridge_runs_no_task(monkeypatch):
    def boom(**_kw):
        raise OSError("down")
    monkeypatch.setattr(client, "status", boom)
    assert client.task_running() is False
    monkeypatch.setattr(client, "status", lambda **_kw: {"mission": {"state": "READY"}})
    assert client.task_running() is True


def test_both_tabs_check_before_they_create_a_mission():
    simple = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text()
    start = simple[simple.index("    def start_task(self)"):]
    assert start.index("task_running()") < start.index("create_live_full_auto(")
    standard = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text()
    assert "import mission_running" in standard
