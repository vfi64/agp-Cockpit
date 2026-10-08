from pathlib import Path


def test_deterministic_startup_wakeup_contract():
    source = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert "AGP_DETERMINISTIC_STARTUP_WAKE_063V" in source
    assert "def reload_exactly_one_chatgpt_tab()" in source
    assert 'return "MULTIPLE_CHATGPT_TABS:" & foundCount' in source
    assert 'return "NO_CHATGPT_TAB"' in source
    assert 'reload tab targetTab of window targetWindow' in source
    assert "timeout_seconds=5.0" in source
    assert "timeout_seconds=12.0" in source
    assert "browser_connecting = not extension_ready" in source

def test_startup_wakeup_is_bounded_and_fail_closed():
    source = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert source.count("reload_exactly_one_chatgpt_tab()") == 2
    assert source.count("wake_ok, wake_note = reload_exactly_one_chatgpt_tab()") == 1
    assert "if not extension_ready:" in source
    assert "if wake_ok:" in source

def test_execution_core_not_modified_by_startup_wakeup():
    bridge = Path("src/agp_cockpit/core/bridge_server.py").read_text(encoding="utf-8")
    content = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert "/v1/turn" in bridge
    assert "SINGLE_STEP" in content
