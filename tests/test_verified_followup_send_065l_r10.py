from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome_extension" / "content.js"

def src():
    return SRC.read_text() + "\n" + SEND_JS

def test_r10_preserves_verified_send_ack():
    s = src()
    assert 'STATE.lastEvent = "SEND_UNCONFIRMED"' in s
    assert 'STATE.lastEvent = "PROMPT_SENT"' in s
    assert "waitForSentUserMessage(" in s
    assert "beforeMessages" in s
    assert "beforeAssistantText" in s

def test_r10_preserves_bounded_wait_and_button_readiness():
    s = src()
    assert "attempt < 20" in s
    assert "setTimeout(resolve, 150)" in s
    assert "button && !button.disabled" in s

def test_r10_preserves_named_enter_pair():
    s = src()
    assert 'new KeyboardEvent("keydown"' in s
    assert 'new KeyboardEvent("keyup"' in s
    assert "el.dispatchEvent(down)" in s
    assert "el.dispatchEvent(up)" in s
