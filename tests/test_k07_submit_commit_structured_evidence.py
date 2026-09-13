from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"chrome_extension/background.js").read_text(encoding="utf-8")
def native(): return TEXT[TEXT.index("// AGP_BROWSER_NATIVE_TRANSPORT_V1"):]
def test_failed_commit_returns_structured_target_and_post_click_evidence():
    n=native()
    assert "send_target:sendTarget" in n
    assert "post_click:await evaluate" in n
    assert "composer_text:" in n
    assert "button_disabled:" in n
    assert "button_aria_disabled:" in n
    assert "hit_testid:" in n
def test_diagnostic_change_does_not_restore_mouse_commit():
    assert '"Input.dispatchMouseEvent"' not in native()
