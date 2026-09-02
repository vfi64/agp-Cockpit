from pathlib import Path

ROOT = Path("/Users/hof/Dropbox/Privat/GitHub/agp-Cockpit")
SRC = ROOT / "chrome_extension" / "content.js"

def src():
    return SRC.read_text()

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

def test_r9_preserves_multiturn_full_auto():
    s = src()
    assert 'run_mode:"FULL_AUTO"' in s
    assert "065 LIVE 3-TURN READ-ONLY PROBE" in s
