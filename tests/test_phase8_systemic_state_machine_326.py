from pathlib import Path

R=Path(__file__).resolve().parents[1]
P7=(R/"chrome_extension/phase7_single_round.js").read_text()
P8=(R/"chrome_extension/phase8_multi_round.js").read_text()
T7=(R/"tests/test_phase7_browser_bridge_controller.py").read_text()

def test_stable_protocol_entry_is_single_architecture():
    assert "currentAssistantProtocolSnapshot()" not in P7
    assert "protocolSnapshot = null" in P7
    assert "waitForCompletedProtocolAssistant" in P7
    assert 'afterFingerprint:""' in P8
    assert "protocolSnapshot:pending" in P8

def test_max_round_boundary_has_no_extra_wait():
    assert 'if(completed>=maxRounds)return {state:"MAX_ROUNDS_REACHED",rounds:completed,last};' in P8

def test_phase7_regression_contract_migrated():
    assert 'waitForCompletedProtocolAssistant:async' in T7
    assert 'source = "pre"' in T7
    assert 'C.waitForCompletedProtocolAssistant(' in T7
    assert 'C.currentAssistantProtocolSnapshot()' not in T7

def test_transport_stays_in_phase7():
    assert "fetch(" not in P8
    assert "/v1/protocol/execute" not in P8

def test_state_machine_markers():
    assert "AGP_PHASE7_STABLE_PROTOCOL_ENTRY_326" in P7
    assert "AGP_PHASE8_PROTOCOL_STATE_MACHINE_326" in P8
