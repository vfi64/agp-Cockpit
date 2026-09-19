import json
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_runtime_server import (
    BridgeRuntimeServer,
)


def _request(
    url,
    token,
    *,
    method="GET",
    body=None,
):
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


def test_http_end_to_end_dry_run(tmp_path):
    runtime = BridgeRuntimeServer(
        tmp_path,
        port=0,
    )
    info = runtime.start()

    try:
        base = f"http://127.0.0.1:{info.port}"

        created = _request(
            base + "/v1/mission",
            info.token,
            method="POST",
            body={
                "title": "http dry run",
                "mission_text": "preview one command",
                "execution_mode": "DRY_RUN",
                "run_mode": "SINGLE_STEP",
            },
        )

        assert (
            created["mission"]["state"]
            == "READY"
        )

        order = json.dumps({
            "kind": "generic",
            "cwd": str(tmp_path),
            "argv": [
                "/usr/bin/printf",
                "SHOULD-NOT-EXECUTE",
            ],
            "timeout_seconds": 5,
            "label": "http dry-run probe",
        })

        from urllib.error import HTTPError
        with pytest.raises(HTTPError) as exc:
            _request(
                base + "/v1/turn",
                info.token,
                method="POST",
                body={
                    "conversation_url": "https://chatgpt.com/c/test",
                    "assistant_text": order,
                    "turn_id": "http-054",
                },
            )
        assert exc.value.code == 410
        payload = json.loads(exc.value.read())
        assert payload["error"] == "LEGACY_TURN_AUTHORITY_RETIRED"
        assert payload["next"] == "/v1/protocol/execute"

    finally:
        runtime.stop()
