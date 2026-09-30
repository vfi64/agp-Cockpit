"""HTTP-level proofs for delivery state, replay re-delivery, provenance and
post-execution operator control (AGP_K07_DELIVERY_STATE_V1)."""
from __future__ import annotations

import hashlib
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.file_loop_orchestrator import REDELIVERY_NOTICE


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


RUNNER = (
    "import sys, json\n"
    "from pathlib import Path\n"
    "n=int(sys.argv[1]);d=Path(__file__).parent\n"
    "marker=d/'runner_count.txt'\n"
    "marker.write_text(str(int(marker.read_text())+1) if marker.exists() else '1')\n"
    "control=d.parent/'pause_during_run.json'\n"
    "if control.exists():\n"
    "    (d.parent/'.local'/'agp-cockpit'/'bridge'/'operator-control.json').write_text(control.read_text())\n"
    "(d/f'{n:03d}_ok_return_bundle.json').write_text(json.dumps({'status':'PASS'}))\n"
)


@pytest.fixture
def bridge(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text(RUNNER, encoding="utf-8")
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()

    def post(path: str, payload: dict) -> dict:
        request = Request(
            f"http://127.0.0.1:{info.port}{path}",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"X-AGP-Token": info.token, "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def get(path: str) -> dict:
        request = Request(f"http://127.0.0.1:{info.port}{path}", headers={"X-AGP-Token": info.token})
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    post.get = get
    try:
        yield tmp_path, post
    finally:
        runtime.stop()


def command(content: str, **extra) -> dict:
    return {"filename": "step.py", "content": content, "message_id": "m", **extra}


def test_unacknowledged_result_is_redelivered_without_reexecution(bridge):
    root, post = bridge
    first = post("/v1/file-loop/command", command(valid_command_file("a")))
    assert first["delivery_pending"] is True and first["replayed"] is False
    replay = post("/v1/file-loop/command", command(valid_command_file("a")))
    assert replay["replayed"] is True
    assert replay["delivery_pending"] is True
    assert replay["prompt"].startswith(REDELIVERY_NOTICE)
    assert replay["result_sha256"] == first["result_sha256"]
    assert (root / "Download" / "runner_count.txt").read_text() == "1"

    ack = post("/v1/file-loop/delivery-ack",
               {"cycle_id": first["cycle_id"], "result_sha256": first["result_sha256"]})
    assert ack["delivery"] == "DELIVERED"
    suppressed = post("/v1/file-loop/command", command(valid_command_file("a")))
    assert suppressed["replayed"] is True and suppressed["delivery_pending"] is False
    assert (root / "Download" / "runner_count.txt").read_text() == "1"


def test_delivery_ack_for_unknown_result_is_rejected(bridge):
    _root, post = bridge
    post("/v1/file-loop/command", command(valid_command_file("a")))
    with pytest.raises(HTTPError) as caught:
        post("/v1/file-loop/delivery-ack", {"result_sha256": "0" * 64})
    assert caught.value.code == 400


def test_content_must_match_materialized_download_hash(bridge):
    root, post = bridge
    content = valid_command_file("a")
    with pytest.raises(HTTPError) as caught:
        post("/v1/file-loop/command", command(content, download_sha256="f" * 64))
    assert caught.value.code == 400
    assert not (root / "Download" / "runner_count.txt").exists()
    ok = post("/v1/file-loop/command",
              command(content, download_sha256=hashlib.sha256(content.encode()).hexdigest()))
    assert ok["state"] == "COMMAND_FILE"


def test_pause_during_execution_holds_continuation_until_resume(bridge):
    root, post = bridge
    (root / "pause_during_run.json").write_text(json.dumps({"generation": 1, "action": "PAUSE"}))
    held = post("/v1/file-loop/command", command(valid_command_file("a")))
    assert held["held"] is True and held["prompt"] is None and held["terminal"] is False
    (root / "pause_during_run.json").unlink()
    (root / ".local/agp-cockpit/bridge/operator-control.json").write_text(
        json.dumps({"generation": 2, "action": "RESUME"})
    )
    resumed = post("/v1/file-loop/command", command(valid_command_file("a")))
    assert resumed["replayed"] is True and resumed["delivery_pending"] is True
    assert resumed["prompt"].startswith(REDELIVERY_NOTICE)
    assert (root / "Download" / "runner_count.txt").read_text() == "1"


def test_stop_during_execution_withholds_result_and_is_terminal(bridge):
    root, post = bridge
    (root / "pause_during_run.json").write_text(json.dumps({"generation": 1, "action": "STOP"}))
    stopped = post("/v1/file-loop/command", command(valid_command_file("a")))
    assert stopped["terminal"] is True and stopped["prompt"] is None
    state = json.loads((root / ".local/agp-cockpit/bridge/file-loop-state.json").read_text())
    assert state["command_history"][-1]["delivery"] == "WITHHELD"


def test_mission_counts_each_executed_step_once_and_never_a_replay(bridge):
    # AGP_K07_STEP_COUNT_V1: live 2026-09-30 showed "Steps 0" after an executed step.
    _root, post = bridge
    post("/v1/mission", {"title": "t", "mission_text": "m", "execution_mode": "LIVE",
                         "run_mode": "FULL_AUTO"})
    first = post("/v1/file-loop/command", command(valid_command_file("a")))
    post("/v1/file-loop/command", command(valid_command_file("a")))  # replay
    mission = post.get("/v1/status")["mission"]
    assert first["replayed"] is False
    assert mission["step_count"] == 1
    assert mission["turn_count"] == 1
