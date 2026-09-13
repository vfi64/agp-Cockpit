from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "chrome_extension" / "content.js"

def text():
    return CONTENT.read_text()

def test_r11_marker():
    assert "AGP_SEND_ACK_FALSE_NEGATIVE_065L_R11" in text()

def test_r11_assistant_activity_ack():
    s = text()
    assert "SEND_ASSISTANT_ACTIVITY_OBSERVED" in s
    assert "authoritative_acceptance:false" in s
    assert "assistantNow !== assistantBefore" in s
    assert "lastAssistantText()" in s

def test_r11_bounded_ack():
    s = text()
    assert "i < 60" in s
    assert "setTimeout(resolve, 250)" in s

def test_r11_keeps_r7_fallback_contract():
    s = text()
    for needle in [
        "attempt < 20",
        "setTimeout(resolve, 150)",
        "button && !button.disabled",
        'new KeyboardEvent("keydown"',
        'new KeyboardEvent("keyup"',
        "el.dispatchEvent(down)",
        "el.dispatchEvent(up)",
    ]:
        assert needle in s

def test_r11_remains_fail_closed():
    s = text()
    assert "SEND_UNCONFIRMED" in s
    assert "if (!acknowledgement.confirmed)" in s
