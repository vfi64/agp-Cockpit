import json
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_runtime_server import (
    BridgeRuntimeServer,
)


def test_diagnostics_endpoint(tmp_path):
    runtime = BridgeRuntimeServer(
        tmp_path,
        port=0,
    )
    info = runtime.start()

    try:
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/diagnostics",
            headers={"X-AGP-Token": info.token},
        )

        with urlopen(req, timeout=3) as response:
            data = json.loads(
                response.read().decode()
            )

        assert data["max_bytes"] == 2 * 1024 * 1024
        assert data["backup_count"] == 4
        assert data["log_path"].endswith(
            ".local/agp-cockpit/logs/bridge.log"
        )
    finally:
        runtime.stop()
