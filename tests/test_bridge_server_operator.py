import json
import threading
import time
from pathlib import Path
from urllib.error import HTTPError
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


def test_operator_stop_terminates_active_file_loop_runner(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text(
        "import sys, time\n"
        "from pathlib import Path\n"
        "n=int(sys.argv[1]); d=Path(__file__).parent\n"
        "time.sleep(5)\n"
        "(d/f'{n:03d}_ok_return_bundle.json').write_text('{}')\n",
        encoding="utf-8",
    )
    server = CockpitBridgeServer(
        tmp_path,
        config=BridgeServerConfig(host="127.0.0.1", port=0, token="stop-token"),
    )
    server.start()
    try:
        base = f"http://127.0.0.1:{server._server.server_address[1]}"
        command = (
            "import argparse\nfrom pathlib import Path\n"
            'COMMAND = ["agentic-kit", "stop-test"]\n'
            'RETURN_BUNDLE = "return_bundle.json"\n'
            "def main():\n"
            "    parser = argparse.ArgumentParser()\n"
            '    parser.add_argument("--self-test", action="store_true")\n'
            "    parser.parse_args()\n"
            '    Path(RETURN_BUNDLE).write_text("{}")\n'
            'if __name__ == "__main__":\n'
            "    main()\n"
        )
        holder = {}

        def submit_command():
            holder["result"] = _request(
                base + "/v1/file-loop/command",
                "stop-token",
                method="POST",
                body={"filename": "stop_command.py", "content": command},
            )

        thread = threading.Thread(target=submit_command)
        thread.start()
        deadline = time.monotonic() + 3
        while not server._run_next_controller.snapshot()["active"] and time.monotonic() < deadline:
            time.sleep(0.01)
        assert server._run_next_controller.snapshot()["active"] is True

        stopped = _request(
            base + "/v1/file-loop/control",
            "stop-token",
            method="POST",
            body={"action": "STOP"},
        )
        thread.join(timeout=3)

        assert stopped["process_stop"]["requested"] is True
        assert thread.is_alive() is False
        result_path = Path(holder["result"]["result_file"])
        result = json.loads(result_path.read_text(encoding="utf-8"))
        assert result["status"] == "unknown"
        assert result["outcome"] == "OUTCOME_UNKNOWN"
        assert result["termination"] == "STOPPED"

        try:
            _request(
                base + "/v1/file-loop/command",
                "stop-token",
                method="POST",
                body={"filename": "after_stop.py", "content": command},
            )
        except HTTPError as exc:
            assert exc.code == 400
        else:
            raise AssertionError("STOP must reject later command-file admission")
    finally:
        server.stop()
