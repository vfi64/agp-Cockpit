from __future__ import annotations

import json
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_server import BridgeServerConfig, CockpitBridgeServer


def _post(url: str, token: str, payload: dict) -> dict:
    request = Request(
        url,
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-AGP-Token": token,
        },
    )
    with urlopen(request, timeout=3) as response:
        return json.loads(response.read().decode("utf-8"))


def test_start_request_reads_handshake_from_bridge_runtime_root(tmp_path, monkeypatch):
    from agp_cockpit.core import runtime_identity

    repository = tmp_path / "repo"
    (repository / "Download").mkdir(parents=True)
    (repository / "Download" / "run_next.py").write_text("# runner\n", encoding="utf-8")
    staged = tmp_path / "staged-extension"
    staged.mkdir()
    (staged / "manifest.json").write_text(
        json.dumps({"version": "0.3.2"}), encoding="utf-8"
    )
    (staged / "build_identity.js").write_text(
        'globalThis.AGP_EXTENSION_BUILD_ID = "build-a";\n',
        encoding="utf-8",
    )
    (staged / ".agp-stage.json").write_text(
        json.dumps(
            {
                "repository_root": str(repository.resolve()),
                "download_directory": str((repository / "Download").resolve()),
                "run_next": str((repository / "Download" / "run_next.py").resolve()),
                "version": "0.3.2",
                "build_id": "build-a",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(runtime_identity, "local_extension_root", lambda: staged)

    bridge_root = tmp_path / "production-runtime"
    server = CockpitBridgeServer(
        repository,
        config=BridgeServerConfig(host="127.0.0.1", port=0, token="test-token"),
        runtime_root=bridge_root,
    )
    server.start()
    try:
        port = server._server.server_address[1]
        base = f"http://127.0.0.1:{port}"
        handshake = _post(
            f"{base}/v1/client-event",
            "test-token",
            {
                "event": "EXTENSION_HANDSHAKE",
                "details": {
                    "version": "0.3.2",
                    "build_id": "build-a",
                    "page_url": "https://chatgpt.com/c/current",
                },
            },
        )
        assert handshake["ok"] is True
        assert (bridge_root / "extension.json").is_file()
        assert not (repository / ".local/agp-cockpit/bridge/extension.json").exists()

        mission = _post(
            f"{base}/v1/mission",
            "test-token",
            {
                "title": "test",
                "mission_text": "test",
                "conversation_url": "https://chatgpt.com/c/current",
                "execution_mode": "LIVE",
                "run_mode": "FULL_AUTO",
            },
        )["mission"]
        request = _post(
            f"{base}/v1/task/start-request",
            "test-token",
            {"mission_id": mission["mission_id"], "task_id": "task-1"},
        )
        assert request["mission_id"] == mission["mission_id"]
        assert request["task_id"] == "task-1"
    finally:
        server.stop()
