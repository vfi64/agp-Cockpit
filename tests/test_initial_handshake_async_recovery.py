from pathlib import Path


def test_initial_handshake_absence_is_connecting_not_immediate_warning():
    s = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert "AGP_INITIAL_HANDSHAKE_ASYNC_063R2" in s
    assert "AGP_DETERMINISTIC_STARTUP_WAKE_063V" in s
    assert "timeout_seconds=5.0" in s
    assert "timeout_seconds=12.0" in s
    assert "browser_connecting = not extension_ready" in s
    assert "timeout_seconds=180.0" in s
    block = s[s.index("AGP_INITIAL_HANDSHAKE_ASYNC_063R2"):]
    before_gui = block.split("try:\n        run_legacy_gui()", 1)[0]
    assert "show_startup_guidance(message)" not in before_gui
    assert "_browser_readiness_worker" in before_gui
    assert 'data["browser_state"] = "CONNECTED"' in before_gui
