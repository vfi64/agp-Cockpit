from pathlib import Path
TEXT=Path("chrome_extension/background.js").read_text(encoding="utf-8")
N=TEXT[TEXT.index("// AGP_BROWSER_NATIVE_TRANSPORT_V1"):]

def test_preserves_proven_input_transport():
    assert '"Input.insertText"' in N
    assert 'stage:"INSERT_NOT_VERIFIED"' in N

def test_submit_only_boundary_is_keydown_enter():
    assert '"Input.dispatchKeyEvent"' in N
    assert 'type:"keyDown"' in N
    assert 'key:"Enter"' in N
    assert 'code:"Enter"' in N
    assert 'text:"\\\\r"' in N
    assert 'unmodifiedText:"\\\\r"' in N
    assert 'type:"keyUp"' in N

def test_raw_keydown_submit_is_gone():
    assert 'type:"rawKeyDown"' not in N

def test_failed_mouse_submit_stays_removed():
    assert '"Input.dispatchMouseEvent"' not in N

def test_readiness_and_exact_commit_contract_preserved():
    assert 'stage:"SEND_BUTTON_NOT_READY"' in N
    assert "document.elementFromPoint(x, y)" in N
    assert 'stage:"USER_TURN_COMMITTED"' in N
    assert 'stage:"USER_TURN_NOT_COMMITTED"' in N
    assert "exact_user_message_found" in N
