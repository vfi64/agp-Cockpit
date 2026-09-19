from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"chrome_extension/background.js").read_text(encoding="utf-8")
def test_native_commit_uses_send_control():
    assert 'button[data-testid="send-button"]' in TEXT
    assert '"Input.dispatchKeyEvent"' in TEXT
    assert 'type:"keyDown"' in TEXT
    assert 'type:"keyUp"' in TEXT
    assert 'stage:"SEND_BUTTON_NOT_READY"' in TEXT
def test_native_transport_no_longer_uses_mouse_commit():
    native=TEXT[TEXT.index("// AGP_BROWSER_NATIVE_TRANSPORT_V1"):]
    assert '"Input.dispatchMouseEvent"' not in native
