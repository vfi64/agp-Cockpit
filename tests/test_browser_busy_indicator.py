from pathlib import Path

CONTENT = Path("chrome_extension/content.js")

def _source():
    return CONTENT.read_text(encoding="utf-8")

def test_busy_indicator_contract_present():
    s = _source()
    assert "AGP_BROWSER_BUSY_INDICATOR_064_R2" in s
    assert "agp-spinner" in s
    assert "@keyframes agp-cockpit-spin" in s
    assert "if (STATE.running)" in s
    assert "STATE.waitingForAssistant" in s
    assert "\"ChatGPT arbeitet…\"" in s
    assert "\"Cockpit arbeitet…\"" in s

def test_busy_indicator_is_status_only():
    s = _source()
    block = s[s.index("AGP_BROWSER_BUSY_INDICATOR_064_R2"):]
    assert "role\", \"status" in block
    assert "aria-live\", \"polite" in block

def test_existing_live_probe_contract_remains():
    s = _source()
    assert "title:\"061 LIVE READ-ONLY PROBE\"" in s
    assert "STATE.turns += 1" in s
    assert "assertExactLiveProbeWorkOrder" in s
