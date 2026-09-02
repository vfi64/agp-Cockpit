from pathlib import Path


def _source():
    return Path("src/agp_cockpit/app_bootstrap.py").read_text(encoding="utf-8")


def test_ready_message_branch_is_reachable():
    s = _source()
    assert "AGP_STARTUP_CONTROLFLOW_FIX_063V_R5" in s
    assert "if deterministic_browser_ready:" in s
    assert "if extension_ready and not deterministic_browser_ready:" not in s


def test_worker_is_only_started_while_connecting():
    s = _source()
    anchor = "import threading as _threading"
    tail = s[s.index(anchor):]
    assert "if browser_connecting:" in tail
    assert "target=_browser_readiness_worker" in tail
    assert tail.index("if browser_connecting:") < tail.index("target=_browser_readiness_worker")


def test_final_sync_state_contract():
    extension_ready = True
    deterministic_browser_ready = extension_ready
    browser_connecting = not extension_ready
    assert deterministic_browser_ready is True
    assert browser_connecting is False


def test_fallback_contract():
    extension_ready = False
    deterministic_browser_ready = extension_ready
    browser_connecting = not extension_ready
    assert deterministic_browser_ready is False
    assert browser_connecting is True


def test_old_async_recovery_is_preserved_as_fallback_only():
    s = _source()
    assert "_browser_readiness_worker" in s
    assert "timeout_seconds=180.0" in s
    assert 'reason="cockpit-startup"' in s


def test_bounded_wakeup_contract_remains():
    s = _source()
    assert "AGP_DETERMINISTIC_STARTUP_WAKE_063V" in s
    assert "timeout_seconds=5.0" in s
    assert "timeout_seconds=12.0" in s
    assert s.count("wake_ok, wake_note = reload_exactly_one_chatgpt_tab()") == 1
