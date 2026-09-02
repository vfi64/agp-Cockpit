from pathlib import Path


def test_deterministic_handshake_skips_redundant_refresh():
    s = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert "AGP_SKIP_REDUNDANT_POST_HANDSHAKE_REFRESH_063V_R3" in s
    assert "deterministic_browser_ready = extension_ready" in s
    assert "if deterministic_browser_ready:" in s
    assert "if extension_ready and not deterministic_browser_ready:" not in s
    tail = s[s.index("import threading as _threading"):]
    assert "if browser_connecting:" in tail
    assert tail.index("if browser_connecting:") < tail.index("target=_browser_readiness_worker")


def test_legacy_async_recovery_is_still_present():
    s = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert "_browser_readiness_worker" in s
    assert "timeout_seconds=180.0" in s
    assert "request_browser_refresh(" in s


def test_063v_wakeup_contract_remains_present():
    s = Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")
    assert "AGP_DETERMINISTIC_STARTUP_WAKE_063V" in s
    assert "timeout_seconds=5.0" in s
    assert "timeout_seconds=12.0" in s
    assert "reload_exactly_one_chatgpt_tab" in s


def test_execution_core_and_overlay_are_untouched():
    bridge = Path("src/agp_cockpit/core/bridge_server.py").read_text(encoding="utf-8")
    content = Path("chrome_extension/content.js").read_text(encoding="utf-8")
    assert "/v1/turn" in bridge
    assert "LIVE_PROBE" in content
    assert "SINGLE_STEP" in content
    assert "agp-head" in content
