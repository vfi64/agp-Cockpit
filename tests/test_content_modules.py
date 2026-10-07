"""content.js split (owner 2026-10-07: "Zerlegung von content.js Modul für Modul").

content.js stays the controller (STATE, mission loop, actions); each split-off module is a
classic content script with one frozen namespace, loaded by the manifest before content.js.
Module 1, AGP_PANEL_MODULE_V1: cockpit_panel.js renders the overlay from STATE and calls back
into the controller; it never talks to the bridge, the service worker or the ChatGPT page.
The size of content.js may only fall (ratchet). Real-Chromium checks:
tests/e2e/test_066_actual_contentjs_send_ack.spec.js and test_066_b1_d1_bootstrap_trace.spec.js
load the real stack, panel included."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "chrome_extension"
CONTENT = (EXT / "content.js").read_text(encoding="utf-8")
PANEL = (EXT / "cockpit_panel.js").read_text(encoding="utf-8")

# Ratchet: lower it whenever a module leaves content.js; never raise it.
CONTENT_MAX_LINES = 3789


def test_manifest_loads_every_module_before_the_controller():
    js = json.loads((EXT / "manifest.json").read_text(encoding="utf-8"))["content_scripts"][0]["js"]
    assert js[-1] == "content.js"
    assert js.index("cockpit_panel.js") < js.index("content.js")


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
