from pathlib import Path


def test_gui_authority_forwarded_at_all_legacy_calls():
    s=Path("src/agp_cockpit/app_bootstrap.py").read_text()
    assert "run_legacy_gui(root)" not in s
    assert s.count("run_legacy_gui(root, local_contract=local_contract)") == 3
def test_k07_assistant_wait_is_bounded_and_accounting_remains_transition_derived():
    s=Path("chrome_extension/content.js").read_text()
    assert "AGP_K07_ASSISTANT_WAIT_TIMEOUT_1360" in s
    assert "K07_ASSISTANT_RESPONSE_TIMEOUT after 180s" in s
    assert "assistantWaitStartedAt" in s
    assert "STATE.turns += 1;" in s
