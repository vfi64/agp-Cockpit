from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_server import BridgeServerConfig, CockpitBridgeServer
from agp_cockpit.core.task_contract import LocalTaskContract


def server(tmp_path):
    contract = LocalTaskContract(
        tmp_path,
        allowed_effects=frozenset({"E2"}),
        allowed_tools=frozenset({"false", "true"}),
        allow_network=False,
    )
    instance = CockpitBridgeServer(
        tmp_path,
        config=BridgeServerConfig(host="127.0.0.1", port=0, token="t"),
        runtime_root=tmp_path / "rt",
        local_task_contract=contract,
    )
    instance.start()
    return instance


def event(instance, details):
    port = instance._server.server_address[1]
    req = Request(
        f"http://127.0.0.1:{port}/v1/client-event",
        data=json.dumps({
            "event": "RESULT_DELIVERED",
            "details": details,
        }).encode(),
        method="POST",
        headers={
            "X-AGP-Token": "t",
            "Content-Type": "application/json",
        },
    )
    with urlopen(req, timeout=3) as response:
        return json.loads(response.read())


def seed(instance, action_id):
    controller = instance._durable_controller("vertical")
    controller.accept_remote_action(action_id, {"x": action_id})
    attempt = controller.begin_attempt(action_id)
    controller.record_local_result(action_id, attempt, "FAIL", "failure")
    return controller


def test_ack_is_correlated_and_idempotent(tmp_path):
    instance = server(tmp_path)
    try:
        controller = seed(instance, "a1")
        assert [x["action_id"] for x in controller.pending_results()] == ["a1"]

        first = event(
            instance,
            {"session_id": "vertical", "action_id": "a1"},
        )
        assert first["result_delivery"] == "ACKNOWLEDGED"
        assert controller.pending_results() == []

        second = event(
            instance,
            {"session_id": "vertical", "action_id": "a1"},
        )
        assert second["result_delivery"] == "ALREADY_ACKNOWLEDGED"

        assert controller.accept_remote_action("a2", {"x": "a2"}) == "NEW"
    finally:
        instance.stop()


def test_wrong_action_fails_closed(tmp_path):
    instance = server(tmp_path)
    try:
        controller = seed(instance, "a1")
        try:
            event(
                instance,
                {"session_id": "vertical", "action_id": "wrong"},
            )
            assert False, "wrong action acknowledgement must fail"
        except HTTPError as exc:
            assert exc.code == 400

        assert [x["action_id"] for x in controller.pending_results()] == ["a1"]
    finally:
        instance.stop()
