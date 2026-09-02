from pathlib import Path


def test_bootstrap_prefers_existing_chatgpt_tab():
    source = Path(
        "src/agp_cockpit/app_bootstrap.py"
    ).read_text(encoding="utf-8")

    assert 'repeat with w in windows' in source
    assert 'u starts with "https://chatgpt.com/"' in source
    assert 'make new tab' in source


def test_handshake_is_rate_limited_and_url_sensitive():
    source = Path(
        "chrome_extension/content.js"
    ).read_text(encoding="utf-8")

    assert "lastHandshakeUrl" in source
    assert "lastHandshakeAt" in source
    assert "now - STATE.lastHandshakeAt < 60000" in source
    assert "setInterval(sendHandshake, 15000)" in source
    assert "setInterval(sendHandshake, 5000)" not in source


def test_existing_execution_core_markers_preserved():
    source = Path(
        "chrome_extension/content.js"
    ).read_text(encoding="utf-8")

    assert "ASSISTANT_RESPONSE_COMPLETE" in source
    assert "MISSION_BOOTSTRAP_SENT" in source
    assert "NEXT_STEP_PROMPT_SENT" in source
