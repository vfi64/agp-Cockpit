from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome_extension" / "content.js"

def src():
    return SRC.read_text() + "\n" + SEND_JS

def test_r10_preserves_verified_send_ack():
    s = src()
    assert 'STATE.lastEvent = "SEND_INDETERMINATE"' in s   # AGP_DEGRADED_DOM_PATH_REMOVED_V1
    assert 'STATE.lastEvent = "PROMPT_SENT"' in s
    assert "waitForSentUserMessage(" in s
    assert "beforeMessages" in s
    assert "beforeAssistantText" in s
