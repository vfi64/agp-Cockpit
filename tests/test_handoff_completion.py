import json
from types import SimpleNamespace

import pytest

from agp_cockpit.core import handoff_completion as hc
from agp_cockpit.core.task_controller import DurableTaskController


def valid_command_file(label: str) -> str:
    return (
        "import argparse\nfrom pathlib import Path\n"
        f'COMMAND = ["agentic-kit", "{label}"]\n'
        'RETURN_BUNDLE = "return_bundle.json"\n'
        "def main():\n"
        "    parser = argparse.ArgumentParser()\n"
        '    parser.add_argument("--self-test", action="store_true")\n'
        "    parser.parse_args()\n"
        '    Path(RETURN_BUNDLE).write_text("{}")\n'
        'if __name__ == "__main__":\n'
        "    main()\n"
    )


@pytest.fixture
def handoff(tmp_path, monkeypatch):
    root = tmp_path
    (root / hc.PACKAGE).mkdir(parents=True)
    (root / "Download").mkdir()
    runtime = root / "runtime"
    runtime.mkdir()
    before = hc.package_snapshot(root)
    for name in hc.FILES:
        (root / hc.PACKAGE / name).write_text(json.dumps({"status": "PASS", "generated_head": "head"}))
    prompt = root / "Download/1467_START_NEW_CHAT_DETAILED_PROMPT.md"
    prompt.write_text("Read-only intake")
    bundle = root / "Download/1467_return_bundle.json"
    bundle.write_text(json.dumps({
        "status": "PASS", "package_path": str(root / hc.PACKAGE),
        "detailed_start_prompt_path": str(prompt),
        "execution": {"returncode": 0, "cwd": str(root),
                      "argv": ["agentic-kit", "transfer", "chat-switch-complete", "--json"]},
    }))
    run = SimpleNamespace(return_bundle=bundle, runner_returncode=0, artifact_kind="return_bundle", step=1467)
    monkeypatch.setattr(hc, "validate_with_kit", lambda root: {"status": "PASS", "findings": []})
    monkeypatch.setattr(hc.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout="head\n"))
    controller = DurableTaskController("task", runtime / "tasks.sqlite3")
    controller.store.set_runtime_contract("task", scope={"completion_contract": {"kind": hc.CONTRACT_KIND}})
    yield root, runtime, before, run, controller
    controller.close()


def prepare(handoff):
    root, runtime, before, run, _ = handoff
    return hc.prepare_receipt(root, runtime, mission_id="mission", task_id="task", cycle_id="cycle", run=run, before=before)


def ack(handoff, **overrides):
    root, runtime, _, _, controller = handoff
    receipt = json.loads((runtime / "handoff-completion.json").read_text())
    args = {"mission_id": "mission", "cycle_id": "cycle", "result_sha256": receipt["result_sha256"]}
    args.update(overrides)
    return hc.acknowledge_delivery(root, runtime, controller, **args)


def test_completion_requires_delivery_and_is_idempotent(handoff):
    receipt = prepare(handoff)
    assert receipt["delivered"] is False
    assert handoff[4].snapshot["state"] != "VERIFIED_COMPLETE"
    assert ack(handoff)["state"] == "DONE"
    assert handoff[4].snapshot["state"] == "VERIFIED_COMPLETE"
    assert ack(handoff)["state"] == "DONE"


@pytest.mark.parametrize("field,value", [("mission_id", "old"), ("cycle_id", "other"), ("result_sha256", "wrong")])
def test_foreign_receipt_rejected(handoff, field, value):
    prepare(handoff)
    with pytest.raises(ValueError, match="foreign"):
        ack(handoff, **{field: value})


def test_artifact_change_rejected(handoff):
    prepare(handoff)
    (handoff[0] / hc.PACKAGE / "successor_prompt.md").write_text("changed")
    with pytest.raises(ValueError, match="changed"):
        ack(handoff)


def test_stale_package_rejected(handoff):
    handoff[2].update(hc.package_snapshot(handoff[0]))
    with pytest.raises(ValueError, match="freshly"):
        prepare(handoff)


def test_failure_is_not_completion(handoff):
    handoff[3].return_bundle.write_text('{"status":"FAIL"}')
    assert prepare(handoff) is None


def test_contract_is_not_inferred_from_pass(handoff):
    prepare(handoff)
    handoff[4].store.set_runtime_contract("task", scope={})
    with pytest.raises(ValueError, match="foreign"):
        ack(handoff)


def test_runner_failure_rejected(handoff):
    handoff[3].runner_returncode = 1
    with pytest.raises(ValueError, match="runner"):
        prepare(handoff)


def test_operator_stop_during_validation_prevents_completion(handoff):
    receipt = prepare(handoff)
    def stopped():
        raise ValueError("operator stopped")
    with pytest.raises(ValueError, match="operator stopped"):
        hc.acknowledge_delivery(handoff[0], handoff[1], handoff[4],
                                mission_id="mission", cycle_id="cycle",
                                result_sha256=receipt["result_sha256"], require_active=stopped)
    assert handoff[4].snapshot["state"] != "VERIFIED_COMPLETE"


def test_kit_failure_rejected(handoff, monkeypatch):
    def reject(root):
        raise ValueError("installed Kit rejected handoff artifacts")
    monkeypatch.setattr(hc, "validate_with_kit", reject)
    with pytest.raises(ValueError, match="Kit rejected"):
        prepare(handoff)


def test_http_result_delivery_finishes_task_not_next_command(handoff, monkeypatch):
    import os
    from urllib.request import Request, urlopen

    from agp_cockpit.core import bridge_server
    from agp_cockpit.core.start_request import StartRequestStore

    root, runtime, _, run, controller = handoff
    run.run_next_output = root / "Download/output.txt"
    run.run_next_output.write_text("PASS")

    def consume(*args, **kwargs):
        for name in hc.FILES:
            path = root / hc.PACKAGE / name
            stamp = path.stat().st_mtime_ns + 1_000_000
            os.utime(path, ns=(stamp, stamp))
        return SimpleNamespace(state=SimpleNamespace(value="COMMAND_FILE"), run=run,
                               human_reason=None, continuation_text="next step", replayed=False,
                               delivery_pending=True)

    monkeypatch.setattr(bridge_server, "consume_command_file", consume)
    server = bridge_server.CockpitBridgeServer(
        root, runtime_root=runtime,
        config=bridge_server.BridgeServerConfig(port=0, token="test"),
    )
    server.start()

    def post(path, body):
        req = Request(f"http://127.0.0.1:{server._server.server_address[1]}{path}",
                      data=json.dumps(body).encode(),
                      headers={"X-AGP-Token": "test", "Content-Type": "application/json"})
        with urlopen(req, timeout=5) as response:
            return json.load(response)

    try:
        mission = post("/v1/mission", {"title": "handoff", "mission_text": "handoff",
                                      "execution_mode": "LIVE", "run_mode": "FULL_AUTO"})["mission"]
        StartRequestStore(runtime).request(mission["mission_id"], task_id=controller.task_id)
        result = post(
            "/v1/file-loop/command",
            {"filename": "1467_test.py", "content": valid_command_file("handoff")},
        )
        assert result["completion_pending"] is True
        assert result["terminal"] is False
        assert "Acknowledge receipt only" in result["prompt"]
        assert controller.snapshot["state"] != "VERIFIED_COMPLETE"
        body = {"cycle_id": result["cycle_id"], "result_sha256": result["result_sha256"]}
        assert post("/v1/file-loop/result-delivered", body)["state"] == "DONE"
        assert server.engine.runtime.state.state == "DONE"
        assert controller.snapshot["state"] == "VERIFIED_COMPLETE"
        assert post("/v1/file-loop/result-delivered", body)["state"] == "DONE"
    finally:
        server.stop()


def test_task_binding_survives_start_request_invalidation(handoff, monkeypatch):
    # AGP_K07_ACTIVE_TASK_BINDING_V1: live 2026-09-30 showed task_id=null at
    # /command because accepting the start request cleared it.
    import os
    from urllib.request import Request, urlopen

    from agp_cockpit.core import bridge_server
    from agp_cockpit.core.start_request import StartRequestStore

    root, runtime, _, run, controller = handoff
    run.run_next_output = root / "Download/output.txt"
    run.run_next_output.write_text("PASS")

    def consume(*args, **kwargs):
        for name in hc.FILES:
            path = root / hc.PACKAGE / name
            stamp = path.stat().st_mtime_ns + 1_000_000
            os.utime(path, ns=(stamp, stamp))
        return SimpleNamespace(state=SimpleNamespace(value="COMMAND_FILE"), run=run,
                               human_reason=None, continuation_text="next step", replayed=False,
                               delivery_pending=True)

    monkeypatch.setattr(bridge_server, "consume_command_file", consume)
    server = bridge_server.CockpitBridgeServer(
        root, runtime_root=runtime,
        config=bridge_server.BridgeServerConfig(port=0, token="test"),
    )
    server.start()

    def post(path, body):
        req = Request(f"http://127.0.0.1:{server._server.server_address[1]}{path}",
                      data=json.dumps(body).encode(),
                      headers={"X-AGP-Token": "test", "Content-Type": "application/json"})
        with urlopen(req, timeout=5) as response:
            return json.load(response)

    try:
        mission = post("/v1/mission", {"title": "handoff", "mission_text": "handoff",
                                      "execution_mode": "LIVE", "run_mode": "FULL_AUTO"})["mission"]
        request = StartRequestStore(runtime).request(mission["mission_id"], task_id=controller.task_id)
        consumed = post("/v1/client-event", {
            "event": "TASK_START_REQUEST_ACCEPTED",
            "details": {"generation": request["generation"], "request_mission_id": mission["mission_id"]},
        })
        assert consumed.get("task_start_request") == "CONSUMED"
        assert StartRequestStore(runtime).current()["task_id"] == ""
        result = post(
            "/v1/file-loop/command",
            {"filename": "1467_test.py", "content": valid_command_file("handoff")},
        )
        assert result["completion_pending"] is True
        assert result["terminal"] is False
        assert "Acknowledge receipt only" in result["prompt"]
        assert controller.snapshot["state"] != "VERIFIED_COMPLETE"
        body = {"cycle_id": result["cycle_id"], "result_sha256": result["result_sha256"]}
        assert post("/v1/file-loop/result-delivered", body)["state"] == "DONE"
        assert server.engine.runtime.state.state == "DONE"
        assert controller.snapshot["state"] == "VERIFIED_COMPLETE"
        assert post("/v1/file-loop/result-delivered", body)["state"] == "DONE"
    finally:
        server.stop()
