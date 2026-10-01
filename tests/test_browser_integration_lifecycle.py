import json
from pathlib import Path

from agp_cockpit.core.browser_refresh import (
    handled_refresh_path,
    read_browser_refresh_request,
    request_browser_refresh,
)


def test_refresh_request_is_monotonic_and_local(tmp_path):
    first = request_browser_refresh(tmp_path, reason="one")
    second = request_browser_refresh(tmp_path, reason="two")
    assert second.generation > first.generation

    current = read_browser_refresh_request(tmp_path)
    assert current is not None
    assert current.generation == second.generation
    assert handled_refresh_path(tmp_path).name == "handled_refresh.json"


def test_manifest_has_service_worker_and_permissions():
    data = json.loads(
        Path("chrome_extension/manifest.json").read_text(encoding="utf-8")
    )
    assert data["background"]["service_worker"] == "background.js"
    for permission in ("tabs", "storage", "alarms"):
        assert permission in data["permissions"]


def test_content_receives_refresh_generation():
    source = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert "refresh_generation" in source
    assert "AGP_REFRESH_INTEGRATION" in source
    assert "handled_refresh_generation" in source


def test_background_has_reload_loop_guard():
    source = Path("chrome_extension/background.js").read_text(encoding="utf-8")
    assert "generation <= handled" in source
    assert "chrome.runtime.reload()" in source
    assert "Persist the tab work" in source
    assert "setTimeout(() => {\n    chrome.runtime.reload()" not in source
    assert "chrome.tabs.reload(tabId)" in source
    assert "chrome.alarms.create" in source


def test_bridge_uses_handled_refresh_evidence():
    source = Path("src/agp_cockpit/core/bridge_server.py").read_text(encoding="utf-8")
    assert "handled_refresh.json" in source
    assert "client_response[" in source
    assert '"refresh_generation"' in source
    assert "refresh_generation" in source
    assert "handled_refresh_generation" in source


def test_bootstrap_requests_refresh():
    source = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert 'reason="cockpit-startup"' in source
    assert "wait_for_refresh_handled" in source


def test_real_main_window_has_no_manual_refresh_button():
    source = Path("src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert "AGP_BROWSER_REFRESH_BUTTON_062" not in source
    assert "Browser-Verbindung neu laden" not in source
    assert 'reason="cockpit-button"' not in source
