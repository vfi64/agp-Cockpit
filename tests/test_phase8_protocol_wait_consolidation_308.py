from pathlib import Path

R=Path(__file__).resolve().parents[1]
C=(R/"chrome_extension/conversation_contract.js").read_text()
P=(R/"chrome_extension/phase8_multi_round.js").read_text()

def test_phase8_wait_is_protocol_specific():
    assert "waitForCompletedProtocolAssistant" in P
    assert "C.waitForCompletedAssistant({afterFingerprint:last.assistant_fingerprint" not in P

def test_protocol_snapshot_accepts_three_frames():
    sec=C[C.index("async function currentAssistantProtocolSnapshot()"):C.index("AGP_PHASE8_PROTOCOL_WAIT_CONSOLIDATION_308")]
    for m in ("ACTION_BEGIN","RESULT_BEGIN","CONTROL_BEGIN"): assert "AGP_COCKPIT_"+m in sec
    assert sec.count("includeControl: true")==2

def test_phase5_generic_snapshot_unchanged_for_control():
    sec=C[C.index("async function currentAssistantSnapshot()"):C.index("async function waitForCompletedAssistant(")]
    assert "includeControl: true" not in sec
    assert "AGP_COCKPIT_CONTROL_BEGIN" not in sec

def test_protocol_waiter_freshness_and_fail_closed():
    sec=C[C.index("async function waitForCompletedProtocolAssistant("):C.index("globalThis.AGPCockpitConversationContract")]
    assert "currentAssistantProtocolSnapshot()" in sec
    assert "snapshot.fingerprint === afterFingerprint" in sec
    assert "stable >= stablePolls" in sec
    assert "if (!transient) throw err;" in sec
    assert "PHASE8_COMPLETED_PROTOCOL_ASSISTANT_TIMEOUT" in sec

def test_ambiguity_remains_fail_closed():
    assert 'throw new Error("PHASE7_PROTOCOL_FRAME_AMBIGUOUS")' in C
