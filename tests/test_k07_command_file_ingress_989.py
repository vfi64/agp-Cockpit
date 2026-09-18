
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer

ROOT = Path(__file__).resolve().parents[1]

def test_browser_ingress_uses_existing_debugger_and_no_downloads_permission():
    manifest = json.loads((ROOT / "chrome_extension/manifest.json").read_text())
    assert "debugger" in manifest["permissions"]
    assert "downloads" not in manifest["permissions"]
    background = (ROOT / "chrome_extension/background.js").read_text()
    assert "AGP_K07_COMMAND_FILE_FETCH_989" in background
    assert '"Runtime.evaluate"' in background
    assert 'fetch(href, {credentials:"include"})' in background
    assert "chrome.downloads" not in background
    content = (ROOT / "chrome_extension/content.js").read_text()
    assert "AGP_K07_COMMAND_FILE_INGRESS_989" in content
    assert "assistantPythonAttachmentCandidates" in content
    assert 'button[aria-label$=".py"]' in content
    assert "readAssistantButtonAttachment" in content
    assert '[role="dialog"] .cm-content[role="textbox"]' in content
    assert 'startsWith("request-placeholder")' in content
    assert "root.appendChild(actions)" in content
    assert "COMMAND_FILE_ATTACHMENT_PENDING" in content
    assert "attachmentWaitMs < 15000" in content
    assert "Date.now() + 45000" in content
    assert "expected exactly one assistant .py attachment" in content
    assert '"/v1/file-loop/command"' in content

def test_command_file_http_executes_only_through_run_next(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "import json\n"
        "n=int(sys.argv[1]);d=Path(__file__).parent\n"
        "(d/'runner_invoked.json').write_text(json.dumps({'argv':sys.argv[1:]}))\n"
        "(d/f'{n:03d}_ok_return_bundle.json').write_text('{}')\n",
        encoding="utf-8",
    )
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()
    try:
        payload = {
            "filename": "next_command.py",
            "content": "print('safe fixture')\n",
            "href": "https://chatgpt.com/backend-api/files/x",
            "message_id": "m1",
        }
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/file-loop/command",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "X-AGP-Token": info.token,
                "Content-Type": "application/json",
            },
        )
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        assert data["state"] == "COMMAND_FILE"
        assert data["replayed"] is False
        assert data["result_file"].endswith("_return_bundle.json")
        assert Path(data["result_file"]).exists()
        assert "Return exactly one Python command file" in data["prompt"]
        commands = list(download.glob("*_next_command.py"))
        assert len(commands) == 1
        assert commands[0].read_text(encoding="utf-8") == "print('safe fixture')\n"
        assert json.loads((download / "runner_invoked.json").read_text(encoding="utf-8"))["argv"] == ["1"]
        assert Path(data["result_file"]).parent == download
    finally:
        runtime.stop()


def test_file_loop_handler_uses_server_database_path_closure():
    server = (ROOT / "src/agp_cockpit/core/bridge_server.py").read_text()
    assert "durable_db_path = self._durable_db_path" in server
    assert "DurableTaskController(current_task_id, durable_db_path)" in server


def test_concurrent_duplicate_command_file_is_executed_once(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text(
        "import os, sys\n"
        "from pathlib import Path\n"
        "n=int(sys.argv[1]);d=Path(__file__).parent\n"
        "(d/f'runner_invoked_{os.getpid()}.json').write_text('{}')\n"
        "(d/f'{n:03d}_ok_return_bundle.json').write_text('{}')\n",
        encoding="utf-8",
    )
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()
    payload = {
        "filename": "concurrent_command.py",
        "content": "print('safe fixture')\n",
        "href": "https://chatgpt.com/backend-api/files/concurrent",
        "message_id": "concurrent-message",
    }

    def submit():
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/file-loop/command",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "X-AGP-Token": info.token,
                "Content-Type": "application/json",
            },
        )
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            responses = list(executor.map(lambda _: submit(), range(3)))
        assert all(response["state"] == "COMMAND_FILE" for response in responses)
        assert sum(response["replayed"] is False for response in responses) == 1
        assert sum(response["replayed"] is True for response in responses) == 2
        assert len(list(download.glob("runner_invoked_*.json"))) == 1
        assert len(list(download.glob("*_concurrent_command.py"))) == 1
    finally:
        runtime.stop()
