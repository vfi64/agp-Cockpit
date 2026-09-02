import json
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_runtime_server import (
    BridgeRuntimeServer,
)


def _get_json(url, token):
    req = Request(
        url,
        headers={"X-AGP-Token": token},
    )
    with urlopen(req, timeout=3) as response:
        return json.loads(response.read().decode())


def test_runtime_server_persists_token_and_serves_status(tmp_path):
    runtime = BridgeRuntimeServer(
        tmp_path,
        port=0,
    )
    info = runtime.start()

    try:
        assert info.token
        assert (
            tmp_path
            / ".local/agp-cockpit/bridge/token.txt"
        ).exists()

        status = _get_json(
            f"http://127.0.0.1:{info.port}/v1/status",
            info.token,
        )
        assert status["state"] == "IDLE"
    finally:
        runtime.stop()

    again = BridgeRuntimeServer(
        tmp_path,
        port=0,
    )
    assert again.info.token == info.token
