"""DOM bundle 2026-10-07: AGP_UI_FINGERPRINT_V1 (step 5), AGP_DOM_SHAPE_SNAPSHOT_V1 (step 2),
AGP_SEND_OUTCOME_FIRST_V1 (step 1 rest), AGP_K07_TERMINAL_REGENERATE_V1,
AGP_LOST_REPLY_CHECK_V1 and AGP_RECOVER_HINT_FOLLOWS_OFFER_V1. The helpers themselves run in
node: tests/dom_observe_browser.cjs and tests/remote_file_regenerate_browser.cjs."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from agp_cockpit.core import bridge_server, ui_observation
from agp_cockpit.core.standard_task_progress import stopped_by_lost_reply

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "chrome_extension/content.js").read_text(encoding="utf-8")
EVIDENCE = (ROOT / "chrome_extension/native_message_evidence.js").read_text(encoding="utf-8")
PANEL = (ROOT / "src/agp_cockpit/ui/standard_tasks_panel.py").read_text(encoding="utf-8")


# --- AGP_UI_FINGERPRINT_V1 ------------------------------------------------------------------

def test_a_new_fingerprint_is_a_new_variant_with_time_and_predecessor(tmp_path):
    assert ui_observation.variant_line(tmp_path).endswith("(nach dem nächsten Task-Start)")
    first = ui_observation.record_variant(tmp_path, {"fingerprint": "aaaa1111", "ui_signature": ["testid:x"]},
                                          now=1000.0)
    assert first["previous"] == "" and first["since"] == 1000.0
    assert ui_observation.record_variant(tmp_path, {"fingerprint": "aaaa1111"}, now=2000.0) is None
    second = ui_observation.record_variant(tmp_path, {"fingerprint": "bbbb2222", "ui_signature": ["testid:y"]},
                                           now=3000.0)
    assert second["previous"] == "aaaa1111" and second["previous_signature"] == ["testid:x"]
    line = ui_observation.variant_line(tmp_path, now=3000.0 + 60)
    assert line.startswith("ChatGPT-Oberfläche: Variante bbbb2222 · seit ") and "NEU (vorher aaaa1111)" in line
    assert "NEU" not in ui_observation.variant_line(tmp_path, now=3000.0 + 2 * 86400)
    assert ui_observation.record_variant(tmp_path, {}) is None


def test_the_bridge_logs_a_changed_variant_once(tmp_path):
    events = []
    diag = SimpleNamespace(event=lambda name, **kw: events.append((name, kw["details"])))
    state = SimpleNamespace(mission_id="m")
    bridge_server._observe_ui(tmp_path, "MISSION_TOUCHPOINT_SELFTEST",
                              {"fingerprint": "aaaa1111", "ui_signature": ["testid:a", "testid:b"]}, state, diag)
    assert events == []                                       # the first variant is no change
    bridge_server._observe_ui(tmp_path, "MISSION_TOUCHPOINT_SELFTEST",
                              {"fingerprint": "cccc3333", "ui_signature": ["testid:b", "testid:c"]}, state, diag)
    assert events == [("UI_VARIANT_CHANGED", {"fingerprint": "cccc3333", "previous": "aaaa1111",
                                              "added": ["testid:c"], "removed": ["testid:a"]})]
    bridge_server._observe_ui(tmp_path, "TICK_ERROR", {"fingerprint": "dddd"}, state, diag)
    assert len(events) == 1


def test_the_selftest_sends_the_fingerprint():
    block = CONTENT[CONTENT.index('await clientEvent("MISSION_TOUCHPOINT_SELFTEST", {'):]
    block = block[:block.index("});")]
    assert "fingerprint:touchpoints.fingerprint" in block and "ui_signature:touchpoints.ui_signature" in block
    check = EVIDENCE[EVIDENCE.index("function agpMissionTouchpointCheck("):EVIDENCE.index("function agpFnv1a(")]
    assert "agpUiFingerprint(composer, form)" in check
    assert "fingerprint:ui.fingerprint, ui_signature:ui.signature" in check


def test_the_system_tab_shows_the_variant():
    source = (ROOT / "src/agp_cockpit/ui/main_window.py").read_text(encoding="utf-8")
    assert "textvariable=self.ui_variant_var" in source and "variant_line(self.repository_root)" in source


# --- AGP_DOM_SHAPE_SNAPSHOT_V1 ------------------------------------------------------------

def test_shapes_go_to_files_and_the_log_keeps_the_name(tmp_path):
    details = {"message": "Error: K07 command-file browser download timed out", "mission_id": "m",
               "dom_shape": {"composer_form": {"t": "form"}, "nodes": 7, "alerts": ["Herunterladen fehlgeschlagen"]}}
    slim = bridge_server._slim_dom_shape(tmp_path, "TICK_ERROR", details)
    assert slim["dom_shape"]["nodes"] == 7 and slim["dom_shape"]["file"].endswith("-TICK_ERROR.json")
    assert details["dom_shape"]["nodes"] == 7                  # the caller's dict is untouched
    stored = ui_observation.runtime_dir(tmp_path, *ui_observation.SNAPSHOT_DIR) / slim["dom_shape"]["file"]
    payload = json.loads(stored.read_text(encoding="utf-8"))
    assert payload["shape"]["alerts"] == ["Herunterladen fehlgeschlagen"] and payload["mission_id"] == "m"
    assert bridge_server._slim_dom_shape(tmp_path, "X", {"a": 1}) == {"a": 1}
    for n in range(35):
        ui_observation.store_dom_shape(tmp_path, "E", {"dom_shape": {"nodes": 1}}, now=1_000_000 + n)
    assert len(list(stored.parent.glob("*.json"))) == ui_observation.KEEP_SNAPSHOTS


def test_failures_after_the_start_send_their_shape():
    tick_error = CONTENT[CONTENT.index('await clientEvent("TICK_ERROR", {'):][:300]
    assert "failureDomShape()" in tick_error
    indeterminate = CONTENT[CONTENT.index('await clientEvent("SEND_INDETERMINATE", {'):][:300]
    assert "failureDomShape()" in indeterminate
    helper = CONTENT[CONTENT.index("  function failureDomShape() {"):CONTENT.index("  function submitComposerWithoutButton(")]
    assert "agpDomShape({composer_form:form, last_assistant:" in helper
    assert "'[role=\"alert\"]'" in helper and "text.length <= 120" in helper


# --- AGP_SEND_OUTCOME_FIRST_V1 --------------------------------------------------------------

def test_the_retry_falls_back_without_a_send_button():
    retry = CONTENT[CONTENT.index("const retryButton = sendButton(retryComposer);"):]
    retry = retry[:retry.index("transport.transition(SEND_TRANSPORT.RETRY_ATTEMPTED")]
    assert "retryVia = submitComposerWithoutButton(retryComposer);" in retry
    assert "if (retryVia) {" in retry
    helper = CONTENT[CONTENT.index("  function submitComposerWithoutButton("):CONTENT.index("  async function sendPromptDomDegraded(")]
    assert "form.requestSubmit();" in helper and 'key:"Enter"' in helper


# --- AGP_K07_TERMINAL_REGENERATE_V1 / AGP_LOST_REPLY_CHECK_V1 / AGP_RECOVER_HINT_FOLLOWS_OFFER_V1

def test_a_lost_terminal_file_is_regenerated():
    block = CONTENT[CONTENT.index("  async function requestRemoteFileRegeneration("):]
    block = block[:block.index("if (candidates.length !== 1) return false;")]
    assert "candidates = expectedStepTerminalCandidates();" in block


def test_a_lost_reply_is_checked_like_a_late_one():
    stopped = {"state": "STOPPED", "last_error": "Error: K07 command-file browser download timed out"}
    assert stopped_by_lost_reply(stopped) == "nach der nicht ladbaren Abschlussdatei"
    assert stopped_by_lost_reply({"state": "STOPPED",
                                  "last_summary": "K07_ASSISTANT_RESPONSE_TIMEOUT after 181s"}) == \
        "nach der Zeitüberschreitung"
    assert stopped_by_lost_reply({"state": "STOPPED", "last_error": "something else"}) == ""
    assert stopped_by_lost_reply({"state": "BLOCKED", "last_error": "browser download timed out"}) == ""
    assert "lost = stopped_by_lost_reply(current)" in PANEL
    assert 'cause=getattr(self, "_late_cause", "")' in PANEL


def test_the_recover_sentence_follows_the_offer():
    from agp_cockpit.ui import standard_tasks_panel as panel

    class Var:
        def __init__(self, value):
            self.value = value

        def get(self):
            return self.value

        def set(self, value):
            self.value = value

    fake = SimpleNamespace(recover_offered=False,
                           status_var=Var("Abschließen · Gestoppt\nAbschließen" + panel.RECOVER_HINT))
    panel.StandardTasksPanel._retract_recover_hint(fake)
    assert panel.RECOVER_HINT not in fake.status_var.get() and panel.RECOVER_CLEARED in fake.status_var.get()
    fake = SimpleNamespace(recover_offered=True, status_var=Var("X" + panel.RECOVER_HINT))
    panel.StandardTasksPanel._retract_recover_hint(fake)
    assert panel.RECOVER_HINT in fake.status_var.get()
