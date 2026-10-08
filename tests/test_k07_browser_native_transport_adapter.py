import json
from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / "chrome_extension" / "manifest.json").read_text())
BACKGROUND = (ROOT / "chrome_extension" / "background.js").read_text()
CONTENT = (ROOT / "chrome_extension" / "content.js").read_text() + "\n" + SEND_JS
NATIVE = (ROOT / "chrome_extension" / "browser_native_transport.js").read_text()

def test_manifest_enables_debugger_and_loads_adapter_before_content():
    assert "debugger" in MANIFEST["permissions"]
    block = next(
        b for b in MANIFEST["content_scripts"]
        if any("chatgpt.com" in m for m in b.get("matches", []))
    )
    js = block["js"]
    assert "browser_native_transport.js" in js
    assert js.index("browser_native_transport.js") < js.index("content.js")

def test_background_uses_cdp_native_input_and_detaches():
    assert "AGP_BROWSER_NATIVE_TRANSPORT_V1" in BACKGROUND
    assert "chrome.debugger.attach" in BACKGROUND
    assert '"Input.insertText"' in BACKGROUND
    # Commit contract migrated after real evidence 850: preserve proven text
    # insertion and submit through the trusted CDP keyboard path.
    assert '"Input.dispatchKeyEvent"' in BACKGROUND
    assert 'type:"keyDown"' in BACKGROUND
    assert 'type:"keyUp"' in BACKGROUND
    assert 'key:"Enter"' in BACKGROUND
    assert 'button[data-testid="send-button"]' in BACKGROUND
    assert 'stage:"SEND_BUTTON_NOT_READY"' in BACKGROUND
    assert "chrome.debugger.detach" in BACKGROUND
    assert 'stage:"USER_TURN_COMMITTED"' in BACKGROUND
    assert '"USER_TURN_NOT_COMMITTED"' in BACKGROUND
    assert "exact_user_message_found" in BACKGROUND

def test_native_module_focuses_and_uses_runtime_message():
    assert "AGPBrowserNativeTransport" in NATIVE
    assert "chrome.runtime.sendMessage" in NATIVE
    assert "composer.focus()" in NATIVE
    assert ".textContent = text" not in NATIVE

def test_primary_sender_is_native_and_dom_fallback_is_disabled():
    # AGP_DEGRADED_DOM_PATH_REMOVED_V1: the native transport is the only sender; its failure stops.
    assert "async function sendPromptNative(prompt)" in CONTENT
    assert "async function sendPrompt(prompt)" in CONTENT
    for gone in ("sendPromptDomDegraded", "AGP_ALLOW_DEGRADED_DOM_FALLBACK", "submitComposerWithoutButton",
                 "DOM_TRANSPORT_DEGRADED_FALLBACK"):
        assert gone not in CONTENT, gone
    start = CONTENT.index("async function sendPrompt(prompt)")
    end = CONTENT.index("\n    return Object.freeze(", start)
    wrapper = CONTENT[start:end]
    assert "return await sendPromptNative(prompt)" in wrapper
    failed = wrapper[wrapper.index("async function sendPromptFailed("):]
    assert failed.count("throw error;") == 1

def test_native_acceptance_requires_conversation_evidence_and_fails_loud():
    start = CONTENT.index("async function sendPromptNative(prompt)")
    end = CONTENT.index("async function sendPrompt(prompt)", start)
    native = CONTENT[start:end]
    assert 'nativeAck.stage || "") !== "USER_TURN_COMMITTED"' in native
    assert "NATIVE_USER_TURN_COMMITTED" in native
    assert "NATIVE_SEND_ACCEPTED" in native
    assert 'native_stage:"USER_TURN_COMMITTED"' in native
