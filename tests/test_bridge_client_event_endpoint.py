import json
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_runtime_server import (
    BridgeRuntimeServer,
)


def test_client_event_is_logged(tmp_path):
    runtime = BridgeRuntimeServer(
        tmp_path,
        port=0,
    )
    info = runtime.start()

    try:
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/client-event",
            method="POST",
            data=json.dumps({
                "event": "MISSION_BOOTSTRAP_SENT",
                "details": {"chars": 123},
            }).encode(),
            headers={
                "X-AGP-Token": info.token,
                "Content-Type": "application/json",
            },
        )

        with urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())

        assert data["ok"] is True

        text = runtime.server.diag.log_path.read_text(
            encoding="utf-8"
        )
        assert "MISSION_BOOTSTRAP_SENT" in text
        assert '"component": "chrome"' in text
    finally:
        runtime.stop()
