"""AGP_MISSION_TOUCHPOINT_SELFTEST_V1 (Slice C, 2026-10-05).

The mission start checks composer, composer form and an enabled file input in
that form before it cleans, attaches or sends anything. Behavior on real
Chromium: tests/e2e/test_mission_touchpoint_selftest.spec.js and
tests/e2e/test_066_actual_contentjs_send_ack.spec.js. These checks pin the
order in content.js and the bridge/Cockpit handling.
"""
from pathlib import Path

from agp_cockpit.core.bridge_runtime import BridgeRuntime

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")
EVIDENCE = (ROOT / "chrome_extension" / "native_message_evidence.js").read_text(encoding="utf-8")
PANEL = (ROOT / "src" / "agp_cockpit" / "ui" / "simple_task_panel.py").read_text(encoding="utf-8")


def test_selftest_runs_before_the_composer_is_touched():
    start = CONTENT.index("AGP_MISSION_TOUCHPOINT_SELFTEST_V1: every composer touchpoint")
    for later in (
        "AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1: the expected step",
        'chrome.runtime.sendMessage({type:"AGP_K07_CLEAN_COMPOSER"})',
        'chrome.runtime.sendMessage({type:"AGP_K07_ATTACH_FILES", files:[digestPath]})',
        "await sendPrompt(bootstrapText);",
    ):
        assert start < CONTENT.index(later), later
    block = CONTENT[start:CONTENT.index("AGP_K07_EXPECTED_STEP_ATTACHMENT_IDENTITY_V1: the expected step")]
    assert "Date.now() + 8000" in block
    assert 'clientEvent("MISSION_TOUCHPOINT_SELFTEST"' in block
    assert 'await stop(message, "MISSION_TOUCHPOINT_SELFTEST_FAILED");' in block
    assert "throw new Error(message);" in block
    assert 'reason:"selftest_unavailable"' in block  # fail closed without the helper


def test_check_is_bound_to_the_resolved_composer_form():
    start = EVIDENCE.index("function agpMissionTouchpointCheck(resolveComposer)")
    fn = EVIDENCE[start:EVIDENCE.index("function agpMissionTouchpointMessage", start)]
    assert 'composer.closest("form")' in fn
    assert "form.querySelectorAll('input[type=\"file\"]')" in fn
    assert "document.querySelectorAll('input[type" not in fn
    for reason in ("composer_not_found", "composer_form_not_found", "file_input_not_found"):
        assert f'reason = "{reason}"' in fn


def test_bridge_records_the_failure_without_blocking_the_transport(tmp_path):
    runtime = BridgeRuntime(tmp_path)
    state = runtime.create_mission(title="Task", mission_text="x")
    assert runtime.record_browser_transport(
        "MISSION_TOUCHPOINT_SELFTEST_FAILED",
        {"mission_id": state.mission_id, "reason": "AGP_TOUCHPOINT_COMPOSER_NOT_FOUND: Selbsttest"},
    )
    assert runtime.state.browser_transport_event == "MISSION_TOUCHPOINT_SELFTEST_FAILED"
    assert runtime.state.browser_transport_note.startswith("AGP_TOUCHPOINT_COMPOSER_NOT_FOUND")
    assert runtime.state.browser_transport_blocked is False


def test_cockpit_panel_names_the_selftest_failure():
    assert 'if transport_event == "MISSION_TOUCHPOINT_SELFTEST_FAILED":' in PANEL
    assert "Selbsttest vor dem Start fehlgeschlagen — nichts gesendet" in PANEL
