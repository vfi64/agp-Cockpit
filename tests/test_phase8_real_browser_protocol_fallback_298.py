from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "chrome_extension/conversation_contract.js").read_text()

def test_real_chat_text_fallback_exists():
    assert "AGP_PHASE8_PROTOCOL_RENDERING_FALLBACK_298" in SRC
    assert "uniqueCandidates.length === 0" in SRC
    assert "assistant.innerText || assistant.textContent" in SRC
    assert 'source = "assistant-text"' in SRC

def test_pre_path_remains_preferred_and_strict():
    assert "uniqueCandidates.length === 1" in SRC
    assert 'PHASE7_PROTOCOL_BLOCK_NOT_PURE_FRAME' in SRC
    assert 'source = "pre"' in SRC

def test_ambiguous_pre_blocks_still_fail_closed():
    assert "PHASE7_PROTOCOL_BLOCK_COUNT expected=1 actual=${uniqueCandidates.length}" in SRC

def test_text_fallback_requires_protocol_marker():
    assert 'frame.startsWith("AGP_COCKPIT_ACTION_BEGIN")' in SRC
    assert 'frame.startsWith("AGP_COCKPIT_RESULT_BEGIN")' in SRC

def test_snapshot_reports_dynamic_source():
    assert "    source,\n    rawProtocolBlockCount:" in SRC
