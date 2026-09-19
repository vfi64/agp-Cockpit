import json
import time
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer


def test_extension_handshake_via_client_event(tmp_path):
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()
    try:
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/client-event",
            method="POST",
            data=json.dumps({
                "event": "EXTENSION_HANDSHAKE",
                "details": {
                    "version": "0.2.0",
                    "page_url": "https://chatgpt.com/c/test",
                },
            }).encode(),
            headers={
                "X-AGP-Token": info.token,
                "Content-Type": "application/json",
            },
        )
        with urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
        assert data["ok"] is True
        path = tmp_path / ".local/agp-cockpit/bridge/extension.json"
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["version"] == "0.2.0"
        assert saved["page_url"].startswith("https://chatgpt.com/")
        assert time.time() - saved["timestamp_unix"] < 5
    finally:
        runtime.stop()
