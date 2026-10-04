"""AGP_K07_TERMINAL_REPLY_FILE_V1 (D4): terminal remote answers are
step-scoped JSON files, parsed strictly and bound to the expected step."""
from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer
from agp_cockpit.core.download_ingress import read_downloaded_command
from agp_cockpit.core.terminal_reply import parse_terminal_reply, record_terminal_reply


def body(state="NEEDS_HUMAN", reason="Push needs credentials", **extra):
    return json.dumps({"state": state, "reason": reason, **extra})


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("1480_agp_terminal.py", body(), "filename"),
        ("agp_terminal.json", body(), "filename"),
        ("1480_agp_terminal.json", "[]", "JSON object"),
        ("1480_agp_terminal.json", "{", "valid JSON"),
        ("1480_agp_terminal.json", body(state="PASS"), "DONE or NEEDS_HUMAN"),
        ("1480_agp_terminal.json", body(reason="  "), "reason required"),
        ("1480_agp_terminal.json", body(command="rm -rf /"), "unknown keys"),
        ("1480_agp_terminal.json", body(step=1479), "does not match"),
        ("1480_agp_terminal.json", body(reason="x" * 17000), "16 KiB"),
    ],
)
def test_parse_rejects_everything_but_the_strict_schema(filename, content, message):
    with pytest.raises(ValueError, match=message):
        parse_terminal_reply(filename, content)


def test_record_binds_to_expected_step_and_is_idempotent(tmp_path):
    reply = parse_terminal_reply("1480_agp_terminal.json", body(step=1480))
    with pytest.raises(ValueError, match="not the expected step 1481"):
        record_terminal_reply(tmp_path, reply, body(step=1480), 1481)
    assert record_terminal_reply(tmp_path, reply, body(step=1480), 1480) is False
    assert record_terminal_reply(tmp_path, reply, body(step=1480), 1481) is True
    other = parse_terminal_reply("1480_agp_terminal.json", body(reason="different"))
    with pytest.raises(ValueError, match="conflicts"):
        record_terminal_reply(tmp_path, other, body(reason="different"), 1481)


def test_browser_download_of_terminal_file_is_read_as_json(tmp_path):
    download = tmp_path / "Download"
    download.mkdir()
    (download / "1480_agp_terminal (1).json").write_text(body(), encoding="utf-8")
    name, content, kind = read_downloaded_command(
        download / "1480_agp_terminal (1).json", "1480_agp_terminal.json", tmp_path
    )
    assert (name, kind) == ("1480_agp_terminal.json", "application/json")
    assert json.loads(content)["state"] == "NEEDS_HUMAN"


@pytest.fixture
def bridge(tmp_path):
    (tmp_path / "Download").mkdir()
    (tmp_path / "Download" / "1479_previous.py").write_text("# executed\n")
    runtime = BridgeRuntimeServer(tmp_path, port=0)
    info = runtime.start()

    def call(path: str, payload: dict | None = None) -> dict:
        request = Request(
            f"http://127.0.0.1:{info.port}{path}",
            method="POST" if payload is not None else "GET",
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers={"X-AGP-Token": info.token, "Content-Type": "application/json"},
        )
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        yield tmp_path, call
    finally:
        runtime.stop()


def start_mission(call):
    call("/v1/mission", {"title": "t", "mission_text": "m", "execution_mode": "LIVE",
                         "run_mode": "FULL_AUTO"})


def test_needs_human_file_ends_mission_with_reason(bridge):
    root, call = bridge
    start_mission(call)
    result = call("/v1/file-loop/terminal",
                  {"filename": "1480_agp_terminal.json", "content": body()})
    assert result["state"] == "NEEDS_HUMAN" and result["terminal"] is True
    assert result["replayed"] is False
    mission = call("/v1/status")["mission"]
    assert mission["state"] == "NEEDS_HUMAN"
    assert mission["last_summary"] == "Push needs credentials"
    assert (root / "Download" / "1480_agp_terminal.json").is_file()
    again = call("/v1/file-loop/terminal",
                 {"filename": "1480_agp_terminal.json", "content": body()})
    assert again["replayed"] is True and again["state"] == "NEEDS_HUMAN"


def test_done_without_completion_contract_is_remote_declared(bridge):
    _root, call = bridge
    start_mission(call)
    result = call("/v1/file-loop/terminal",
                  {"filename": "1480_agp_terminal.json", "content": body("DONE", "Release tagged")})
    assert result["state"] == "DONE" and result["authority"] == "remote-declared"
    assert call("/v1/status")["mission"]["state"] == "DONE"


def test_wrong_step_or_download_mismatch_is_rejected(bridge):
    _root, call = bridge
    start_mission(call)
    for payload in (
        {"filename": "1479_agp_terminal.json", "content": body()},
        {"filename": "1480_agp_terminal.json", "content": body(), "download_sha256": "0" * 64},
    ):
        with pytest.raises(HTTPError) as error:
            call("/v1/file-loop/terminal", payload)
        assert error.value.code == 400
    assert call("/v1/status")["mission"]["state"] != "NEEDS_HUMAN"


def test_command_endpoint_never_accepts_a_terminal_file(bridge):
    _root, call = bridge
    with pytest.raises(HTTPError):
        call("/v1/file-loop/command", {"filename": "1480_agp_terminal.json", "content": body()})


def test_malformed_terminal_reply_of_a_running_mission_is_corrected(bridge):
    """AGP_TERMINAL_REPLY_CORRECTION_V1 (live 2026-10-04, step 1724: keys "outcome" and
    "sweep_findings" stopped Pflege although its work was complete)."""
    root, call = bridge
    with pytest.raises(HTTPError):   # no running mission: still a plain rejection
        call("/v1/file-loop/terminal", {"filename": "1480_agp_terminal.json",
                                        "content": body("DONE", "ok", outcome="nothing")})
    start_mission(call)
    result = call("/v1/file-loop/terminal", {"filename": "1480_agp_terminal.json",
                                             "content": body("DONE", "ok", outcome="nothing")})
    assert result["state"] == "CONTINUE" and result["terminal"] is False
    assert result["next_step"] == 1481 and "1481_agp_terminal.json" in result["prompt"]
    assert "unknown keys: outcome" in result["prompt"] and '"reason"' in result["prompt"]
    assert json.loads((root / "Download" / "1480_agp_rejected.json").read_text())["count"] == 1
    assert call("/v1/status")["mission"]["state"] not in ("NEEDS_HUMAN", "STOPPED", "DONE")
    corrected = call("/v1/file-loop/terminal", {"filename": "1481_agp_terminal.json",
                                                "content": body("DONE", "nothing to maintain")})
    assert corrected["state"] == "DONE"


def test_terminal_corrections_are_bounded(bridge):
    root, call = bridge
    start_mission(call)
    step = 1480
    for _ in range(3):
        result = call("/v1/file-loop/terminal", {"filename": f"{step}_agp_terminal.json",
                                                 "content": body("DONE", "ok", extra=1)})
        assert result["state"] == "CONTINUE"
        step = result["next_step"]
    last = call("/v1/file-loop/terminal", {"filename": f"{step}_agp_terminal.json",
                                           "content": body("DONE", "ok", extra=1)})
    assert last["state"] == "NEEDS_HUMAN" and last["terminal"] is True
