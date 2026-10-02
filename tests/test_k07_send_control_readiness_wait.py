from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"chrome_extension/background.js").read_text(encoding="utf-8")

def native():
    return TEXT[TEXT.index("// AGP_BROWSER_NATIVE_TRANSPORT_V1"):]

def test_send_control_wait_is_bounded():
    n=native()
    # AGP_SEND_READY_AFTER_UPLOAD_V1: 600 x 50 ms = 30 s (an uploading
    # attachment keeps the send control disabled).
    assert "for (let attempt = 0; attempt < 600; attempt += 1)" in n
    assert "setTimeout(resolve, 50)" in n
    assert "readiness_wait_ms:30000" in n

def test_readiness_requires_actionable_hit_tested_target():
    n=native()
    assert 'record.aria_disabled !== "true"' in n
    assert 'record.pointer_events !== "none"' in n
    assert "record.hit_matches" in n
    assert "document.elementFromPoint(x, y)" in n

def test_failure_returns_structured_candidate_diagnostics():
    n=native()
    assert 'stage:"SEND_BUTTON_NOT_READY"' in n
    assert "send_diagnostics:sendDiagnostics" in n
    assert "readiness_attempt" in n

def test_commit_contract_is_preserved():
    n=native()
    assert '"Input.dispatchKeyEvent"' in n
    assert 'stage:"USER_TURN_COMMITTED"' in n
    assert '"USER_TURN_NOT_COMMITTED"' in n
    assert "exact_user_message_found" in n

def test_no_mouse_submit_regression():
    assert '"Input.dispatchMouseEvent"' not in native()
