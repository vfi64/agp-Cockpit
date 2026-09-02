import json
import time
from pathlib import Path

from agp_cockpit.core.browser_readiness import (
    snapshot_browser_readiness,
    start_browser_readiness_watch,
)


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_snapshot_rejects_old_refresh_generation(tmp_path):
    requested_at = time.time()
    _write(
        tmp_path / ".local/agp-cockpit/browser/handled_refresh.json",
        {"generation": 41, "timestamp_unix": requested_at + 1},
    )
    _write(
        tmp_path / ".local/agp-cockpit/bridge/extension.json",
        {
            "timestamp_unix": requested_at + 1,
            "version": "0.3.0",
            "page_url": "https://chatgpt.com/c/test",
        },
    )
    snapshot = snapshot_browser_readiness(
        tmp_path,
        expected_generation=42,
        requested_at_unix=requested_at,
    )
    assert snapshot.ready is False


def test_snapshot_rejects_stale_extension_handshake(tmp_path):
    requested_at = time.time()
    _write(
        tmp_path / ".local/agp-cockpit/browser/handled_refresh.json",
        {"generation": 42, "timestamp_unix": requested_at + 1},
    )
    _write(
        tmp_path / ".local/agp-cockpit/bridge/extension.json",
        {
            "timestamp_unix": requested_at - 1,
            "version": "0.3.0",
            "page_url": "https://chatgpt.com/c/test",
        },
    )
    snapshot = snapshot_browser_readiness(
        tmp_path,
        expected_generation=42,
        requested_at_unix=requested_at,
    )
    assert snapshot.ready is False


def test_background_watch_promotes_late_success(tmp_path):
    requested_at = time.time()
    _write(
        tmp_path / ".local/agp-cockpit/startup/status.json",
        {
            "bridge_ready": True,
            "extension_ready": False,
            "message": "Browser-Verbindung wird hergestellt.",
        },
    )
    thread = start_browser_readiness_watch(
        tmp_path,
        expected_generation=100,
        requested_at_unix=requested_at,
        timeout_seconds=2.0,
        poll_seconds=0.02,
    )
    time.sleep(0.05)
    _write(
        tmp_path / ".local/agp-cockpit/browser/handled_refresh.json",
        {"generation": 100, "timestamp_unix": requested_at + 0.1},
    )
    _write(
        tmp_path / ".local/agp-cockpit/bridge/extension.json",
        {
            "timestamp_unix": requested_at + 0.1,
            "version": "0.3.0",
            "page_url": "https://chatgpt.com/c/test",
        },
    )
    thread.join(timeout=1.0)
    status = json.loads(
        (tmp_path / ".local/agp-cockpit/startup/status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status["extension_ready"] is True
    assert status["browser_state"] == "CONNECTED"
    assert status["extension_version"] == "0.3.0"
    assert status["handled_refresh_generation"] == 100


def test_app_bootstrap_uses_async_post_refresh_recovery():
    source = Path(
        "src/agp_cockpit/app_bootstrap.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "AGP_INITIAL_HANDSHAKE_ASYNC_063R2" in source
    assert "browser_connecting = not extension_ready" in source
    assert "_browser_readiness_worker" in source
    assert "timeout_seconds=180.0" in source
    assert "wait_for_extension(" in source
    assert "request_browser_refresh(" in source
    assert "wait_for_refresh_handled(" in source
    assert 'data["browser_state"] = "CONNECTED"' in source

    current = source[
        source.index(
            "AGP_INITIAL_HANDSHAKE_ASYNC_063R2"
        ):
    ]
    before_gui = current.split(
        "try:\n        run_legacy_gui()",
        1,
    )[0]
    assert "show_startup_guidance(message)" not in before_gui
