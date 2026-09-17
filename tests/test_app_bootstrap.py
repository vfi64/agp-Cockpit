import json
import time
import subprocess

import pytest

from agp_cockpit.app_bootstrap import (
    StartupStatus,
    recent_extension_handshake,
    write_startup_status,
)


def test_startup_status_written_locally(tmp_path):
    status = StartupStatus(
        chrome_installed=True,
        chrome_started_or_reused=True,
        chatgpt_requested=True,
        bridge_ready=True,
        extension_ready=False,
        message="test",
    )

    path = write_startup_status(
        tmp_path,
        status,
    )

    assert path == (
        tmp_path
        / ".local/agp-cockpit/startup/status.json"
    )

    data = json.loads(
        path.read_text(encoding="utf-8")
    )
    assert data["bridge_ready"] is True
    assert data["extension_ready"] is False


def test_recent_extension_handshake(tmp_path):
    path = (
        tmp_path
        / ".local/agp-cockpit/bridge/extension.json"
    )
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({
            "timestamp_unix": time.time(),
            "version": "0.2.0",
        }),
        encoding="utf-8",
    )

    result = recent_extension_handshake(
        tmp_path,
        max_age_seconds=5,
    )

    assert result is not None
    assert result["version"] == "0.2.0"


@pytest.mark.parametrize("failure", [
    subprocess.TimeoutExpired("osascript", 10),
    OSError("browser automation unavailable"),
    subprocess.CompletedProcess(["osascript"], 1, "", "Apple event failed"),
])
def test_browser_navigation_failure_is_bounded_and_reported(monkeypatch, failure):
    from agp_cockpit import app_bootstrap as boot

    def fake_run(*args, **kwargs):
        assert kwargs["timeout"] == 10
        if isinstance(failure, Exception):
            raise failure
        return failure

    monkeypatch.setattr(subprocess, "run", fake_run)
    requested, note = boot.request_chatgpt_tab()
    assert requested is False
    assert note
    reloaded, note = boot.reload_exactly_one_chatgpt_tab()
    assert reloaded is False
    assert note


@pytest.mark.parametrize("handshake", [None, {"version": "0.3.0"}])
def test_navigation_failure_keeps_desktop_and_runtime_available(monkeypatch, tmp_path, handshake):
    from agp_cockpit import app_bootstrap as boot
    from agp_cockpit.adapters import macos_extension
    import threading

    events = []

    class Runtime:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            events.append("start")

        def stop(self):
            events.append("stop")

    monkeypatch.setattr(boot, "chrome_app_path", lambda: tmp_path)
    monkeypatch.setattr(macos_extension, "stage_extension", lambda root: tmp_path)
    monkeypatch.setattr(boot, "require_stable_production_runtime_root", lambda root: root)
    monkeypatch.setattr(boot, "BridgeRuntimeServer", Runtime)
    monkeypatch.setattr(boot, "request_chatgpt_tab", lambda: (False, "Apple event failed"))
    monkeypatch.setattr(boot, "wait_for_extension", lambda *a, **k: handshake)
    monkeypatch.setattr(boot, "reload_exactly_one_chatgpt_tab", lambda: (False, "no reload"))
    monkeypatch.setattr(threading.Thread, "start", lambda self: None)
    monkeypatch.setattr(boot, "run_legacy_gui", lambda root, local_contract=None: events.append("gui"))
    assert boot.run(tmp_path) == 0
    assert events == ["start", "gui", "stop"]
    status = json.loads((tmp_path / ".local/agp-cockpit/startup/status.json").read_text())
    assert status["bridge_ready"] is True
    assert status["chatgpt_requested"] is False
    assert status["extension_ready"] is bool(handshake)
    assert "Apple event failed" in status["message"]


@pytest.mark.parametrize("output, reloaded", [
    ("RELOADED:https://chatgpt.com/c/test", True),
    ("MULTIPLE_CHATGPT_TABS:2", False),
    ("NO_CHATGPT_TAB", False),
])
def test_browser_navigation_success_preserves_reload_evidence(monkeypatch, output, reloaded):
    from agp_cockpit import app_bootstrap as boot

    monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.CompletedProcess(a, 0, output, ""))
    assert boot.request_chatgpt_tab() == (True, output)
    assert boot.reload_exactly_one_chatgpt_tab() == (reloaded, output)
