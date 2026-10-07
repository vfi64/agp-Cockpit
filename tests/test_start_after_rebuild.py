"""Live 2026-10-07 (r5): „Abschließen“ clicked seven seconds after „Neu bauen und neu starten“
was refused (handshake-build-id-mismatch, the extension still on r4) and left its mission on
READY, which blocked every new start. AGP_START_WAITS_FOR_EXTENSION_V1 and
AGP_START_ABANDONS_ON_FAILURE_V1."""
from __future__ import annotations

from pathlib import Path
from urllib.error import HTTPError

import pytest

from agp_cockpit.core import runtime_identity
from agp_cockpit.core import start_request_client as client

ROOT = Path(__file__).resolve().parents[1]


def test_settling_names_only_reasons_that_pass_by_themselves(monkeypatch):
    monkeypatch.setenv(client.GATE_ENV, "on")
    monkeypatch.setattr(runtime_identity, "runtime_identity_status", lambda *_a, **_k: {
        "ready": False, "reasons": ["handshake-build-id-mismatch", "run-next-missing"]})
    assert client.extension_settling(Path("/r")) == "handshake-build-id-mismatch"
    monkeypatch.setattr(runtime_identity, "runtime_identity_status", lambda *_a, **_k: {
        "ready": False, "reasons": ["run-next-missing"]})
    assert client.extension_settling(Path("/r")) == ""          # not settling: the bridge reports it
    monkeypatch.setattr(runtime_identity, "runtime_identity_status", lambda *_a, **_k: {"ready": True})
    assert client.extension_settling(Path("/r")) == ""


def test_a_refused_start_abandons_exactly_its_mission(monkeypatch, tmp_path):
    token = tmp_path / "token.txt"
    token.write_text("t", encoding="utf-8")
    monkeypatch.setattr(client, "bridge_token_path", lambda: token)
    abandoned = []
    monkeypatch.setattr(client, "abandon_mission", lambda mid, reason, base_url="": abandoned.append((mid, reason)))

    def refuse(*_a, **_k):
        raise HTTPError("http://127.0.0.1/v1/task/start-request", 500, "runtime identity is not ready", {}, None)
    monkeypatch.setattr(client.urllib.request, "urlopen", refuse)
    with pytest.raises(HTTPError):
        client.request_task_start("m-1", task_id="T")
    assert abandoned and abandoned[0][0] == "m-1" and abandoned[0][1].startswith("Start abgelehnt:")


def test_a_named_stop_leaves_another_current_mission_alone(tmp_path):
    import test_human_decision as h
    gen = h._bridge(tmp_path)
    _root, runtime, call = next(gen)
    try:
        current = h.mission(call, runtime)
        answer = call("/v1/file-loop/control", {"action": "STOP", "mission_id": "someone-else", "reason": "x"})
        assert answer == {"stopped": False, "reason": "mission-changed", "mission_state": "READY"}
        assert call("/v1/status")["mission"]["state"] == "READY"
        answer = call("/v1/file-loop/control", {"action": "STOP", "mission_id": current, "reason": "Start abgelehnt"})
        assert answer["mission_state"] == "STOPPED"
    finally:
        gen.close()


def test_both_tabs_wait_for_the_extension_before_they_create_a_mission():
    standard = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")
    start = standard[standard.index("    def start_standard_task("):standard.index("    def _wait_for_extension(")]
    assert start.index("self._wait_for_extension(task.label") < start.index("create_live_full_auto(")
    simple = (ROOT / "src/agp_cockpit/ui/simple_task_panel.py").read_text(encoding="utf-8")
    launch = simple[simple.index("    def _launch("):]
    assert launch.index("extension_settling(self.repository_root)") < launch.index("create_live_full_auto(")
    assert "self.after(1000, lambda: self._launch(auto_finish, attempt + 1))" in launch


def test_the_standard_tab_retries_once_a_second_and_gives_up_with_a_way_out(monkeypatch):
    from types import SimpleNamespace

    from agp_cockpit.ui.standard_tasks_panel import StandardTasksPanel

    class Var:
        value = ""

        def set(self, value):
            self.value = value

    scheduled = []
    panel = SimpleNamespace(repository_root=Path("/r"), status_var=Var(),
                            after=lambda ms, fn: scheduled.append((ms, fn)))
    state = {"reason": "handshake-build-id-mismatch"}
    monkeypatch.setattr(client, "extension_settling", lambda _root: state["reason"])
    retry = object()
    assert StandardTasksPanel._wait_for_extension(panel, "Abschließen", retry) is True
    assert scheduled == [(1000, retry)] and "startet von selbst" in panel.status_var.value
    panel._settle_attempts = client.SETTLE_ATTEMPTS
    assert StandardTasksPanel._wait_for_extension(panel, "Abschließen", retry) is True
    assert panel.status_var.value.startswith("BLOCKED — die Chrome-Erweiterung") and len(scheduled) == 1
    state["reason"] = ""
    assert StandardTasksPanel._wait_for_extension(panel, "Abschließen", retry) is False
    assert panel._settle_attempts == 0
