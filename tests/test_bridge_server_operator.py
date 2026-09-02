import json
from pathlib import Path
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_server import (
    BridgeServerConfig,
    CockpitBridgeServer,
)


def _request(url, token, *, method="GET", body=None):
    data = None
    headers = {"X-AGP-Token": token}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    req = Request(
        url,
        method=method,
        data=data,
        headers=headers,
    )
    with urlopen(req, timeout=3) as response:
        return json.loads(response.read().decode())


def test_operator_endpoints(tmp_path):
    token = "test-token"
    server = CockpitBridgeServer(
        tmp_path,
        config=BridgeServerConfig(
            host="127.0.0.1",
            port=0,
            token=token,
        ),
    )
    server.start()

    try:
        port = server._server.server_address[1]
        base = f"http://127.0.0.1:{port}"

        status = _request(
            base + "/v1/status",
            token,
        )
        assert status["state"] == "IDLE"

        created = _request(
            base + "/v1/mission",
            token,
            method="POST",
            body={
                "title": "test",
                "mission_text": "preview one step",
                "execution_mode": "DRY_RUN",
                "run_mode": "SINGLE_STEP",
            },
        )
        assert (
            created["mission"]["execution_mode"]
            == "DRY_RUN"
        )

        status = _request(
            base + "/v1/status",
            token,
        )
        assert status["state"] == "READY"

    finally:
        server.stop()
