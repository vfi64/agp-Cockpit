from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome_extension" / "content.js"

def src():
    return SRC.read_text() + "\n" + SEND_JS

def test_r9_keeps_r8_verified_send_logic():
    s = src()
    assert "waitForSentUserMessage(" in s
    assert "beforeMessages" in s
    assert "beforeAssistantText" in s
    assert 'STATE.lastEvent = "SEND_UNCONFIRMED"' in s
    assert 'STATE.lastEvent = "PROMPT_SENT"' in s

def test_r9_restores_r7_exact_bounded_loop_contract():
    s = src()
    assert "attempt < 20" in s
    assert "attempt += 1" in s

def test_r9_restores_paired_enter_events():
    s = src()
    assert 'new KeyboardEvent("keydown"' in s
    assert 'new KeyboardEvent("keyup"' in s
