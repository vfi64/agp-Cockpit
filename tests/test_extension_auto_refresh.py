"""AGP_EXTENSION_AUTO_REFRESH_V2: the handshake decides about the extension refresh."""

import json
from pathlib import Path
from urllib.request import Request, urlopen

from agp_cockpit.core.bridge_runtime_server import BridgeRuntimeServer

ROOT = Path(__file__).resolve().parents[1]


def _call(info, path, payload=None):
    request = Request(
        f"http://127.0.0.1:{info.port}{path}",
        method="POST" if payload is not None else "GET",
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"X-AGP-Token": info.token, "Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode())


def _handshake(info, build_id, handled=0):
    return _call(info, "/v1/client-event", {"event": "EXTENSION_HANDSHAKE", "details": {
        "version": "0.0.1", "build_id": build_id, "page_url": "https://chatgpt.com/c/x",
        "handled_refresh_generation": handled}})


def test_outdated_extension_gets_exactly_one_refresh_per_target_build(tmp_path):
    runtime = BridgeRuntimeServer(tmp_path, port=0, runtime_root=tmp_path / "production-runtime")
    info = runtime.start()
    try:
        first = _handshake(info, "old-build")
        expected = first["extension_expected_build_id"]
        assert expected and expected != "old-build"
        generation = first["refresh_generation"]
        assert generation > 0
        request = json.loads((tmp_path / ".local/agp-cockpit/browser/refresh_request.json").read_text())
        assert request["target_build_id"] == expected and request["reason"] == "handshake-build-mismatch"

        # the refresh ran but the old build is still reported: no second request (no reload loop)
        again = _handshake(info, "old-build", handled=generation)
        assert again["refresh_generation"] == generation

        # the staged build reports itself: nothing to do (AGP_SINGLE_REFRESH_V1: no generation at all)
        current = _handshake(info, expected, handled=generation)
        assert current["refresh_generation"] == 0
    finally:
        runtime.stop()


def test_start_request_poll_names_the_staged_build(tmp_path):
    runtime = BridgeRuntimeServer(tmp_path, port=0, runtime_root=tmp_path / "production-runtime")
    info = runtime.start()
    try:
        polled = _call(info, "/v1/task/start-request")
        assert polled["extension_expected_build_id"]
    finally:
        runtime.stop()


def test_extension_reacts_within_seconds_and_reloads_its_tabs():
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    poll = content[content.index("async function pollExplicitTaskStartRequest()"):]
    assert "checkBuildDrift(req.extension_expected_build_id);" in poll[:400]
    drift = content[content.index("function checkBuildDrift("):content.index("async function pollExplicitTaskStartRequest()")]
    assert "void sendHandshake(true);" in drift and "< 10000" in drift
    background = (ROOT / "chrome_extension/background.js").read_text(encoding="utf-8")
    assert "chrome.runtime.onInstalled.addListener(() => { void agpRecoverTabsAfterReload(); });" in background
    assert "await chrome.storage.local.remove(PENDING);" in background


def test_startup_keeps_waiting_when_the_active_tab_is_not_chatgpt():
    source = (ROOT / "src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    block = source[source.index("wake_ok, wake_note = reload_active_chatgpt_tab()"):]
    block = block[:block.index("refresh_confirmed = wait_for_refresh_handled(")]
    assert "return" not in block
    assert 'target_build_id=target_build' in source


def test_panel_shows_mission_turns_and_no_duplicate_mission_line():
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    panel = (ROOT / "chrome_extension/cockpit_panel.js").read_text(encoding="utf-8")   # AGP_PANEL_MODULE_V1
    status = content[content.index("async function refreshStatus()"):]
    status = status[:status.index("return result;")]
    assert 'STATE.note = "";' in status
    assert "STATE.mission ? Number(STATE.mission.turn_count || 0)" in panel


def test_digest_is_attached_once_per_chat_and_manifest():
    """AGP_DIGEST_ONCE_PER_CHAT_V1."""
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    start = content[content.index("const digestPath = String(status.kit_command_digest_path"):]
    start = start[:start.index("await sendPrompt(bootstrapText);")]
    assert "await digestAlreadyInChat(manifestSha)" in start
    assert "was attached earlier in this conversation and is unchanged" in start
    assert start.index("KIT_COMMAND_DIGEST_REUSED") < start.index("AGP_K07_ATTACH_FILES")
    helpers = content[content.index("async function digestAlreadyInChat("):content.index("async function rememberDigest(")]
    assert "entry.sha === sha" in helpers and "< DIGEST_REATTACH_AFTER" in helpers
    assert "const DIGEST_REATTACH_AFTER = 5;" in content


def test_browser_copy_is_removed_only_after_the_bridge_accepted_the_file():
    """AGP_DOWNLOAD_HYGIENE_V1."""
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    command = content[content.index("async function submitAssistantCommandFile("):]
    command = command[:command.index("AGP_K07_ADVANCE_STEP_AFTER_DELIVERY_V1")]
    assert command.index("K07_WORK_ORDER_REJECTED_FOR_CORRECTION") < command.index("void forgetBrowserDownload(fetched);")
    # AGP_REJECTED_ORDER_KEPT_V1: the rejected order's browser copy goes too (the bridge kept it).
    rejected = command[command.index("K07_WORK_ORDER_REJECTED_FOR_CORRECTION"):command.index("return result;")]
    assert "void forgetBrowserDownload(fetched);" in rejected
    assert command.index("K07_FILE_INGRESS_ACCEPTED") < command.rindex("void forgetBrowserDownload(fetched);")
    terminal = content[content.index("async function submitAssistantTerminalReply("):]
    terminal = terminal[:terminal.index("async function submitAssistantCommandFile(")]
    assert terminal.index("K07_TERMINAL_REPLY_OBSERVED") < terminal.index("void forgetBrowserDownload(fetched);")
    background = (ROOT / "chrome_extension/background.js").read_text(encoding="utf-8")
    forget = background[background.index("async function agpForgetCommandFileDownload("):background.index("async function performRefresh(")]
    assert "k07DownloadNameMatches(item.filename, filename)" in forget
    assert forget.index("k07DownloadNameMatches") < forget.index("chrome.downloads.removeFile(id)")


def test_work_orders_get_a_cockpit_tmpdir():
    source = (ROOT / "src/agp_cockpit/core/file_loop_runner.py").read_text(encoding="utf-8")
    # AGP_RUNTIME_HOME_V1: the Cockpit's runtime folder of this repository (A3)
    assert 'runtime_dir(root.resolve(), "tmp", str(step))' in source
    assert 'for name in ("TMPDIR", "TEMP", "TMP"):' in source


def test_live_r6_a_second_request_for_the_same_build_reuses_the_first(tmp_path):
    """AGP_SINGLE_REFRESH_V1 (live 2026-10-07, r5 -> r6): the handshake and the startup worker
    wrote two generations 130 ms apart; the current extension reloaded again and orphaned the
    freshly reloaded ChatGPT tab."""
    from agp_cockpit.core.browser_refresh import request_browser_refresh
    first = request_browser_refresh(tmp_path, reason="handshake-build-mismatch", target_build_id="r6")
    second = request_browser_refresh(tmp_path, reason="staged-extension-version-mismatch", target_build_id="r6")
    assert second.generation == first.generation
    other = request_browser_refresh(tmp_path, reason="staged-extension-version-mismatch", target_build_id="r7")
    assert other.generation > first.generation


def test_live_r6_a_current_extension_marks_a_pending_request_done_instead_of_reloading(tmp_path):
    from agp_cockpit.core.browser_refresh import request_browser_refresh
    runtime = BridgeRuntimeServer(tmp_path, port=0, runtime_root=tmp_path / "production-runtime")
    info = runtime.start()
    try:
        expected = _handshake(info, "old-build")["extension_expected_build_id"]
        first = json.loads((tmp_path / ".local/agp-cockpit/browser/refresh_request.json").read_text())["generation"]
        # the startup worker's request without a target (as in the old flow) arrives later
        later = request_browser_refresh(tmp_path, reason="cockpit-startup").generation
        assert later > first
        current = _handshake(info, expected, handled=first)
        assert current["refresh_generation"] == 0
        marker = json.loads((tmp_path / ".local/agp-cockpit/browser/handled_refresh.json").read_text())
        assert marker["generation"] == later and marker["satisfied_by_current_build"] is True
    finally:
        runtime.stop()


def test_the_extension_guards_its_reload_and_recovers_orphaned_tabs():
    background = (ROOT / "chrome_extension/background.js").read_text(encoding="utf-8")
    assert 'importScripts("build_identity.js");' in background
    refresh = background[background.index("async function performRefresh("):]
    assert refresh.index('reason:"current-build"') < refresh.index("chrome.runtime.reload();")
    orphan = background[background.index("async function agpReloadOrphanedTabs("):]
    assert '{type:"AGP_PING"}' in orphan[:900] and "chrome.tabs.reload(tab.id)" in orphan[:900]
    assert "chrome.runtime.onStartup.addListener(() => { void agpReloadOrphanedTabs(); });" in background
    content = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
    assert 'message.type === "AGP_PING"' in content
    assert "!(expectedBuild && expectedBuild === ownBuild)" in content
