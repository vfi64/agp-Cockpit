
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer

ROOT = Path(__file__).resolve().parents[1]


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

def test_browser_ingress_uses_existing_debugger_and_no_downloads_permission():
    manifest = json.loads((ROOT / "chrome_extension/manifest.json").read_text())
    assert "debugger" in manifest["permissions"]
    assert "downloads" in manifest["permissions"]
    background = (ROOT / "chrome_extension/background.js").read_text()
    assert "AGP_K07_COMMAND_FILE_FETCH_989" in background
    assert '"Runtime.evaluate"' in background
    assert 'fetch(href, {credentials:"include"})' in background
    assert "chrome.downloads.search" in background
    assert "chrome.storage.session" in background
    assert "AGP_K07_ARM_COMMAND_FILE_DOWNLOAD" in background
    assert "AGP_K07_WAIT_COMMAND_FILE_DOWNLOAD" in background
    assert "k07DownloadStartedAfterArm" in background
    content = (ROOT / "chrome_extension/content.js").read_text()
    assert "AGP_K07_COMMAND_FILE_INGRESS_989" in content
    assert "assistantPythonAttachmentCandidates" in content
    assert 'button[aria-label$=".py"]' in content
    assert 'button, [role="button"]' in content
    assert "readAssistantButtonAttachment" in content
    # AGP_DOM_ADAPTER_V1: the file card's download control is named by the page adapter.
    adapter = (ROOT / "chrome_extension/chatgpt_dom.js").read_text()
    assert 'button[aria-label="Datei herunterladen"]' in adapter
    assert '"/v1/file-loop/download"' in content
    assert "K07_ATTACHMENT_DOWNLOAD_USED" in content
    assert '[role="dialog"] .cm-content[role="textbox"]' in adapter   # slice 3c
    assert 'startsWith("request-placeholder")' in content
    assert "root.appendChild(actions)" in content
    assert "COMMAND_FILE_ATTACHMENT_PENDING" in content
    assert "attachmentWaitMs < 15000" in content
    assert "Date.now() + 45000" in content
    assert "expected exactly one assistant .py attachment" in content
    assert '"/v1/file-loop/command"' in content
    assert 'K07_ASSISTANT_ATTACHMENT_OBSERVED' in content
    assert 'lastProcessedAssistantAttachmentKey' in content
    assert 'K07_DUPLICATE_ATTACHMENT_SUPPRESSED' in content
    assert 'assistantAttachmentKey' in content
    assert '[missionId, STATE.runGeneration, messageId, attachment.name' in content
    assert 'captureAssistantBaseline();' in content
    assert 'candidates.filter(item => !baselineNames.has(item.name))' in content
    assert 'K07_FILE_INGRESS_ACCEPTED' in content
    assert 'K07_ASSISTANT_WAIT_TIMEOUT' in content
    assert 'Python-Anhang wird noch vollständig erzeugt' in content
    assert 'if (chatgptGenerationActive()) {' in content
    assert 'WAITING_FOR_PREVIOUS_RESPONSE' in content
    assert 'matchAll(/(?:^|[\\s/])([^\\s/]+\\.py)' in content
    assert '[\\\\s/]' not in content

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
            "content": valid_command_file("check"),
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
        # AGP_ONE_UPLOAD_PER_STEP_V1: the run_next log travels inside the result file.
        assert data["output_file"] is None
        assert "run_next_log" in json.loads(Path(data["result_file"]).read_text(encoding="utf-8"))
        assert data["output_sha256"]
        assert data["result_validation"]["valid"] is True
        assert "Return exactly one Python command file" in data["prompt"]
        commands = list(download.glob("*_next_command.py"))
        assert len(commands) == 1
        assert commands[0].read_text(encoding="utf-8") == valid_command_file("check")
        assert json.loads((download / "runner_invoked.json").read_text(encoding="utf-8"))["argv"] == ["1"]
        assert Path(data["result_file"]).parent == tmp_path / ".local/agp-cockpit/delivery"
        assert len(list(download.glob("*_return_bundle.json"))) == 1   # the local evidence stays in Download
    finally:
        runtime.stop()


def test_command_file_http_rejects_truncated_python_before_acceptance(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text(
        "from pathlib import Path\nPath('runner_invoked').write_text('bad')\n",
        encoding="utf-8",
    )
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()
    try:
        payload = {
            "filename": "next_command.py",
            "content": "def main():\n    if True:\n",
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
        with pytest.raises(HTTPError) as caught:
            urlopen(req, timeout=10)
        assert caught.value.code == 400
        assert "not executable Python" in caught.value.read().decode("utf-8")
        assert not (tmp_path / "file-loop-incoming" / "next_command.py").exists()
        assert not (tmp_path / "runner_invoked").exists()
        assert not list(download.glob("*_next_command.py"))
    finally:
        runtime.stop()


def test_file_loop_handler_uses_server_database_path_closure():
    server = (ROOT / "src/agp_cockpit/core/bridge_server.py").read_text()
    assert 'task_db_path = self.runtime_root / "tasks.sqlite3"' in server
    assert "DurableTaskController(current_task_id, task_db_path)" in server


def test_download_ingress_materializes_only_allowed_download_file(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    command = download / "1464_chat_switch_standard_task.py"
    content = valid_command_file("download")
    command.write_text(content, encoding="utf-8")
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()
    try:
        payload = {
            "filename": command.name,
            "download_path": str(command),
        }
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/file-loop/download",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"X-AGP-Token": info.token, "Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        assert data["stage"] == "COMMAND_FILE_FETCHED"
        assert data["filename"] == command.name
        assert data["content"] == content
    finally:
        runtime.stop()


def test_download_ingress_leaves_semantic_checks_to_command(tmp_path):
    # AGP_INGRESS_SAFETY_ONLY_V1: a truncated or incomplete work order is
    # fetched; /v1/file-loop/command rejects it correctably, not /download.
    download = tmp_path / "Download"
    download.mkdir()
    command = download / "1464_chat_switch_standard_task.py"
    command.write_text("def main():\n    if True:\n", encoding="utf-8")
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()
    try:
        payload = {
            "filename": command.name,
            "download_path": str(command),
        }
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/file-loop/download",
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={"X-AGP-Token": info.token, "Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        assert data["stage"] == "COMMAND_FILE_FETCHED"
        assert data["content"] == "def main():\n    if True:\n"
    finally:
        runtime.stop()


def test_reserve_step_advances_next_local_step(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()
    try:
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/file-loop/reserve-step",
            method="POST",
            data=json.dumps({"step": 1472, "reason": "send-indeterminate"}).encode("utf-8"),
            headers={"X-AGP-Token": info.token, "Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10) as response:
            reserved = json.loads(response.read().decode("utf-8"))
        assert reserved["stage"] == "REMOTE_STEP_RESERVED"
        assert reserved["next_step"] == 1473

        status_req = Request(
            f"http://127.0.0.1:{info.port}/v1/status",
            headers={"X-AGP-Token": info.token},
        )
        with urlopen(status_req, timeout=10) as response:
            status = json.loads(response.read().decode("utf-8"))
        assert status["next_local_step"] == 1473
    finally:
        runtime.stop()


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
        "content": valid_command_file("check"),
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


def test_nonconsecutive_duplicate_command_file_is_replayed(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "run_next.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "n=int(sys.argv[1]);d=Path(__file__).parent\n"
        "marker=d/'runner_count.txt'\n"
        "marker.write_text(str(int(marker.read_text() or '0')+1) if marker.exists() else '1')\n"
        "(d/f'{n:03d}_ok_return_bundle.json').write_text('{}')\n",
        encoding="utf-8",
    )
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()

    def submit(content: str, message_id: str):
        req = Request(
            f"http://127.0.0.1:{info.port}/v1/file-loop/command",
            method="POST",
            data=json.dumps({
                "filename": "command.py",
                "content": content,
                "href": f"https://chatgpt.com/backend-api/files/{message_id}",
                "message_id": message_id,
            }).encode("utf-8"),
            headers={"X-AGP-Token": info.token, "Content-Type": "application/json"},
        )
        with urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        first_content = valid_command_file("first")
        different_content = valid_command_file("different")
        first = submit(first_content, "first")
        submit(different_content, "different")
        replay = submit(first_content, "repeated-first")
        assert first["replayed"] is False
        assert replay["replayed"] is True
        assert replay["result_file"] == first["result_file"]
        assert (download / "runner_count.txt").read_text(encoding="utf-8") == "2"
    finally:
        runtime.stop()
