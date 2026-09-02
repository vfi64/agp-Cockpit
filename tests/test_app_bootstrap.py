import json
import time

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
