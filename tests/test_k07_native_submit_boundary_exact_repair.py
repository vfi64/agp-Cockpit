from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"chrome_extension/background.js").read_text(encoding="utf-8")
def native(): return TEXT[TEXT.index("// AGP_BROWSER_NATIVE_TRANSPORT_V1"):]
def test_send_target_is_hit_tested_before_native_click():
    n=native()
    assert "document.elementFromPoint(x, y)" in n
    assert "button.contains(hit)" in n
    assert "style.pointerEvents" in n
    assert '"Input.dispatchKeyEvent"' in n
def test_commit_remains_persistent_user_turn():
    n=native()
    assert '"USER_TURN_NOT_COMMITTED"' in n
    assert 'stage:"USER_TURN_COMMITTED"' in n
    assert "exact_user_message_found" in n
def test_no_mouse_submit_regression():
    assert '"Input.dispatchMouseEvent"' not in native()
