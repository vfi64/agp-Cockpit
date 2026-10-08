from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "chrome_extension" / "content.js"

def text():
    return CONTENT.read_text() + "\n" + SEND_JS

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

def test_r11_remains_fail_closed():
    s = text()
    # AGP_DEGRADED_DOM_PATH_REMOVED_V1: an unreconciled native send stops as SEND_INDETERMINATE.
    assert 'throw new Error("SEND_INDETERMINATE: user turn not reconciled")' in s
