from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
TEXT=(ROOT/"chrome_extension/background.js").read_text(encoding="utf-8")
def native(): return TEXT[TEXT.index("// AGP_BROWSER_NATIVE_TRANSPORT_V1"):]
def test_failed_commit_returns_structured_target_and_post_click_evidence():
    n=native()
    assert "send_target:sendTarget" in n
    assert "after:lastObserved" in n
    assert "lastObserved.composer_text" in n
    assert "previousIds" in n
    assert "hit_testid:" in n
def test_diagnostic_change_does_not_restore_dom_submit():
    n=native()
    assert "button.click()" not in n
    assert "requestSubmit()" not in n
