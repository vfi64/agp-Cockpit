"""content.js split (owner 2026-10-07: "Zerlegung von content.js Modul für Modul").

content.js stays the controller (STATE, mission loop, actions); each split-off module is a
classic content script with one frozen namespace, loaded by the manifest before content.js.
Module 1, AGP_PANEL_MODULE_V1: cockpit_panel.js renders the overlay from STATE and calls back
into the controller; it never talks to the bridge, the service worker or the ChatGPT page.
Module 2, AGP_INGRESS_MODULE_V1: cockpit_ingress.js takes a file card of the expected step to
the bridge (find, materialize, submit, forget the browser copy); it never sends a prompt and never
renders. Module 3, AGP_SEND_MODULE_V1: cockpit_send.js writes the prompt into the composer and
proves the commit (native submit, commit nonce, bounded retry); it never renders and never runs the
mission loop. Module 4, AGP_LEGACY_PATHS_REMOVED_V1: the operator paths without a button since
2026-09-15 (DRY mission, LIVE probes, Phase 5/7/8) and the content scripts only they loaded are
gone. The size of content.js may only fall (ratchet). Real-Chromium checks:
tests/e2e/test_066_actual_contentjs_send_ack.spec.js and test_066_b1_d1_bootstrap_trace.spec.js
load the real stack, panel included."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "chrome_extension"
CONTENT = (EXT / "content.js").read_text(encoding="utf-8")
PANEL = (EXT / "cockpit_panel.js").read_text(encoding="utf-8")
INGRESS = (EXT / "cockpit_ingress.js").read_text(encoding="utf-8")
SEND = (EXT / "cockpit_send.js").read_text(encoding="utf-8")

# Ratchet: lower it whenever a module leaves content.js; never raise it.
CONTENT_MAX_LINES = 2196


def test_manifest_loads_every_module_before_the_controller():
    js = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["content_scripts"][0]["js"]
    assert js[-1] == "content.js"
    assert js.index("cockpit_panel.js") < js.index("content.js")
    assert js.index("chatgpt_selectors.js") < js.index("cockpit_ingress.js") < js.index("content.js")
    assert js.index("browser_native_transport.js") < js.index("cockpit_send.js") < js.index("content.js")


def test_the_panel_is_one_namespace_that_only_renders_and_calls_back():
    assert PANEL.lstrip().startswith("// AGP_PANEL_MODULE_V1")
    assert "globalThis.AGP_PANEL = Object.freeze({create});" in PANEL
    assert PANEL.count("globalThis.") == 2                    # the export and the build-id read
    for forbidden in ("fetch(", "\"/v1/", "api(", "chrome.runtime.sendMessage", "chrome.debugger", "AGP_SELECTORS",
                      "AGP_DOM", "querySelector"):
        assert forbidden not in PANEL, forbidden
    for callback in ("host.actions.start", "host.actions.stop", "host.actions.next", "host.actions.refresh",
                     "host.actions.toggleTrace()", "host.clientEvent(", "host.retired()", "host.diagnosticsOpen()"):
        assert callback in PANEL, callback


def test_content_js_creates_the_panel_once_and_delegates_render():
    assert CONTENT.count("AGP_PANEL.create(") == 1
    render = CONTENT[CONTENT.index("  function render() {"):]
    render = render[:render.index("\n  }\n")]
    assert "PANEL.render();" in render and "createElement" not in render
    assert "createElement" not in CONTENT                 # no overlay DOM left in the controller
    assert "const STYLE" not in CONTENT and "function btn(" not in CONTENT


def test_content_js_only_shrinks():
    lines = len(CONTENT.splitlines())
    assert lines <= CONTENT_MAX_LINES, (
        f"content.js has {lines} lines (limit {CONTENT_MAX_LINES}); new code belongs in a module")


def test_the_ingress_module_only_takes_files_to_the_bridge():
    assert INGRESS.lstrip().startswith("// AGP_INGRESS_MODULE_V1")
    assert INGRESS.count("globalThis.") == 1 and "globalThis.AGP_INGRESS = Object.freeze({create});" in INGRESS
    for forbidden in ("sendPrompt(", "render(", "AGP_PANEL", "setInterval(", "STATE.running = "):
        assert forbidden not in INGRESS, forbidden
    for route in ('"/v1/file-loop/command"', '"/v1/file-loop/terminal"', '"/v1/file-loop/download"'):
        assert route in INGRESS, route
    assert "return Object.seal(self);" in INGRESS          # one step replaceable in tests, never extended


def test_content_js_creates_the_ingress_once_and_keeps_no_card_logic():
    assert CONTENT.count("AGP_INGRESS.create(") == 1
    for moved in ("function readAssistantButtonAttachment(", "function submitAssistantCommandFile(",
                  "function materializeDownloadedAttachment(", "AGP_DOM.fileCardRow(", "AGP_DOM.previewTextbox("):
        assert moved not in CONTENT, moved


def test_every_ingress_function_content_js_calls_is_bound():
    # Live r11 (2026-10-07, step 1888): the wait observation still called
    # expectedStepAttachmentCandidates() after the move; the ReferenceError appeared only
    # after 20 s of waiting and stopped the run. Every exported name content.js calls must
    # be destructured from INGRESS (or called as INGRESS.<name>).
    exported = re.findall(r"^      (\w+),$", INGRESS[INGRESS.index("Object.assign(self, {"):], re.MULTILINE)
    assert exported
    bound = CONTENT[CONTENT.index("} = INGRESS;") - 400:CONTENT.index("} = INGRESS;")]
    for name in exported:
        bare = re.findall(r"(?<![\w.])" + name + r"\(", CONTENT)
        assert not bare or name in bound, f"content.js calls {name}() but does not bind it from INGRESS"



def test_the_send_module_only_sends_and_never_renders_or_loops():
    assert SEND.lstrip().startswith("// AGP_SEND_MODULE_V1")
    assert SEND.count("globalThis.") == 1 and "globalThis.AGP_SEND = Object.freeze({create});" in SEND
    for forbidden in ("render(", "AGP_PANEL", "AGP_INGRESS", "setInterval(", "STATE.running = ",
                      "PENDING_SEND_TRANSPORT"):
        assert forbidden not in SEND, forbidden
    assert "setPendingSendTransport(" in SEND             # the pending transport stays in the controller


def test_content_js_creates_the_send_module_once_and_keeps_no_send_logic():
    assert CONTENT.count("AGP_SEND.create(") == 1
    for moved in ("function sendPromptNative(", "function waitForSentUserMessage(", "function setComposerText(",
                  "function createSendTransport(", "function clearOwnedDraftBeforeRetry(",
                  "function sendPromptDomDegraded("):
        assert moved not in CONTENT, moved


def test_every_send_name_content_js_uses_is_bound():
    # Same guard as for the ingress (live r11): a moved name used bare in content.js would only
    # fail at run time.
    tail = SEND[SEND.index("return Object.freeze({"):]
    exported = re.findall(r"^      (\w+),$", tail, re.MULTILINE)
    assert "sendPrompt" in exported and "SEND_TRANSPORT" in exported
    end = CONTENT.index("} = SEND;")
    bound = CONTENT[CONTENT.rindex("const {", 0, end):end]
    for name in exported:
        bare = re.findall(r"(?<![\w.$])" + name + r"(?![\w$:])", CONTENT)
        assert not bare or name in bound, f"content.js uses {name} but does not bind it from SEND"


LEGACY_SCRIPTS = ("protocol_action_contract_v1.js", "transport_protocol_v1.js", "conversation_contract.js",
                  "protocol_canonicalizer_v1.js", "phase7_single_round.js", "phase8_multi_round.js")


def test_the_legacy_operator_paths_stay_removed():
    js = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["content_scripts"][0]["js"]
    for name in LEGACY_SCRIPTS:
        assert name not in js and not (EXT / name).exists(), name
    for gone in ("newDryMission", "LiveProbeMission", "LIVE_PROBE", "phase5", "phase7RunOneRound", "phase8",
                 "AGPCockpitPhase", "AGPCockpitConversationContract"):
        assert gone not in CONTENT, gone
    assert "conversationUrl" not in (EXT / "options.js").read_text(encoding="utf-8")
