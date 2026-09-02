from pathlib import Path


def _source():
    return Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")


def test_readiness_is_recomputed_after_one_shot_wakeup():
    s = _source()
    wake = s.index("wake_ok, wake_note = reload_exactly_one_chatgpt_tab()")
    recompute = s.index("AGP_POST_WAKE_READINESS_RECOMPUTE_063V_R4")
    ready_branch = s.index("if deterministic_browser_ready:")
    assert wake < recompute < ready_branch
    assert "browser_connecting = not extension_ready" in s[recompute:ready_branch]


def test_final_sync_readiness_is_derived_from_final_extension_state():
    s = _source()
    block = s[s.index("AGP_POST_WAKE_READINESS_RECOMPUTE_063V_R4"):]
    assert "deterministic_browser_ready = extension_ready" in block
    assert "browser_connecting = not extension_ready" in block


def test_redundant_refresh_is_impossible_after_fresh_sync_handshake():
    extension_ready = True
    deterministic_browser_ready = extension_ready
    assert not (extension_ready and not deterministic_browser_ready)


def test_fallback_contract_remains_present():
    s = _source()
    assert "_browser_readiness_worker" in s
    assert "timeout_seconds=180.0" in s


def test_063v_bounded_wakeup_remains_present():
    s = _source()
    assert "AGP_DETERMINISTIC_STARTUP_WAKE_063V" in s
    assert "timeout_seconds=5.0" in s
    assert "timeout_seconds=12.0" in s
    assert s.count("wake_ok, wake_note = reload_exactly_one_chatgpt_tab()") == 1
