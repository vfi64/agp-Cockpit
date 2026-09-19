import json
from pathlib import Path
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_server import (
    BridgeServerConfig,
    CockpitBridgeServer,
)
from agp_cockpit.core.start_request import StartRequestStore


def test_invalidate_pending_preserves_generation_but_clears_request(tmp_path: Path) -> None:
    store = StartRequestStore(tmp_path)
    requested = store.request("mission-1", task_id="task-1")

    invalidated = store.invalidate_pending()

    assert invalidated == {
        "generation": requested["generation"],
        "mission_id": "",
        "task_id": "",
    }
    assert store.current() == invalidated


def test_next_request_after_invalidation_gets_a_new_generation(tmp_path: Path) -> None:
    store = StartRequestStore(tmp_path)
    first = store.request("mission-1")
    store.invalidate_pending()

    second = store.request("mission-2", task_id="task-2")

    assert second["generation"] == first["generation"] + 1
    assert second["mission_id"] == "mission-2"


def _post(base: str, token: str, path: str, body: dict) -> dict:
    request = Request(
        base + path,
        method="POST",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-AGP-Token": token},
    )
    with urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def test_bridge_start_discards_request_from_previous_lifetime(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    store = StartRequestStore(runtime_root)
    store.request("old-mission", task_id="old-task")
    server = CockpitBridgeServer(
        tmp_path,
        runtime_root=runtime_root,
        config=BridgeServerConfig(host="127.0.0.1", port=0, token="test-token"),
    )

    server.start()
    try:
        assert store.current()["mission_id"] == ""
        assert store.current()["task_id"] == ""
    finally:
        server.stop()


def test_stop_discards_pending_start_request(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    server = CockpitBridgeServer(
        tmp_path,
        runtime_root=runtime_root,
        config=BridgeServerConfig(host="127.0.0.1", port=0, token="test-token"),
    )
    server.start()
    try:
        port = server._server.server_address[1]
        base = f"http://127.0.0.1:{port}"
        created = _post(
            base,
            "test-token",
            "/v1/mission",
            {
                "title": "Standard · Chat wechseln",
                "mission_text": "test",
                "execution_mode": "LIVE",
                "run_mode": "FULL_AUTO",
            },
        )
        mission_id = created["mission"]["mission_id"]
        StartRequestStore(runtime_root).request(mission_id, task_id="task-1")

        stopped = _post(
            base,
            "test-token",
            "/v1/file-loop/control",
            {"action": "STOP"},
        )

        assert stopped["mission_state"] == "STOPPED"
        assert StartRequestStore(runtime_root).current()["mission_id"] == ""
    finally:
        server.stop()
