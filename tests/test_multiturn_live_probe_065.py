from pathlib import Path

SOURCE = Path("chrome_extension/content.js")

def src():
    return SOURCE.read_text(encoding="utf-8")

def test_065_multiturn_contract_exists():
    s = src()
    assert "AGP_MULTITURN_LIVE_PROBE_065" in s
    assert 'title:"065 LIVE 3-TURN READ-ONLY PROBE"' in s
    assert '["/usr/bin/git","status","--short"]' in s
    assert '["/usr/bin/git","branch","--show-current"]' in s
    assert '["/usr/bin/git","log","-1","--oneline"]' in s

def test_065_is_live_single_step_and_bounded():
    s = src()
    assert 'execution_mode:"LIVE"' in s
    assert 'run_mode:"SINGLE_STEP"' in s
    assert "assertBoundedMultiTurnLiveProbeWorkOrder(text);" in s
    assert "timeout > 30" in s
    assert 'data.kind !== "generic"' in s

def test_065_probe_remains_internal_without_normal_ui_entry():
    s = src()
    assert 'btn("LIVE 3-Turn"' not in s
    assert "newMultiTurnLiveProbeMission" in s

def test_existing_live_probe_guard_remains():
    s = src()
    assert "assertExactLiveProbeWorkOrder(text);" in s
    assert 'title:"061 LIVE READ-ONLY PROBE"' in s
