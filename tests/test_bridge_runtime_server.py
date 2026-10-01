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
        assert status["next_local_step"] == 1
    finally:
        runtime.stop()

    again = BridgeRuntimeServer(
        tmp_path,
        port=0,
    )
    assert again.info.token == info.token


def test_runtime_server_starts_without_persisted_mission(tmp_path):
    from agp_cockpit.core.bridge_runtime import BridgeRuntime

    previous = BridgeRuntime(tmp_path)
    created = previous.create_mission(
        title="stale",
        mission_text="must not be exposed after restart",
        execution_mode="LIVE",
        run_mode="FULL_AUTO",
    )
    previous.mark_running()

    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()

    try:
        status = _get_json(
            f"http://127.0.0.1:{info.port}/v1/status",
            info.token,
        )
        assert status["mission"] is None
        assert status["state"] == "IDLE"
        assert "local_authority" in status
        assert (previous.store.root / f"{created.mission_id}.json").exists()
        assert not previous.store.current_path.exists()
    finally:
        runtime.stop()
