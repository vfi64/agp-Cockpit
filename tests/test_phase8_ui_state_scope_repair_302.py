from pathlib import Path
C=(Path(__file__).resolve().parents[1]/"chrome_extension/content.js").read_text()

def test_phase8_ui_does_not_call_undefined_setstatus():
    tail=C[C.index("async function phase8RunMultiRound"):]
    assert "setStatus(" not in tail

def test_phase8_done_updates_canonical_overlay_state():
    assert "AGP_PHASE8_UI_STATE_REPAIR_316" in C
    assert "STATE.turns = Number(out.rounds || 0);" in C
    assert "STATE.note = `Phase 8: ${out.state} (${out.rounds} rounds)`" in C
    assert "STATE.lastEvent = `PHASE8_${out.state}`" in C
    assert 'STATE.lastEvent = "PHASE8_PAUSED"' in C
    assert 'STATE.lastEvent = "PHASE8_RUNNING"' in C
    assert 'STATE.lastEvent = "PHASE8_STOP_REQUESTED"' in C

def test_each_phase8_operator_path_renders():
    section=C[C.index("async function phase8RunMultiRound"):]
    assert section.count("render();") >= 4
