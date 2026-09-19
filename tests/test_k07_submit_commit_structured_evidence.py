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
def test_bounded_canonical_dom_submit_fallback_is_explicit():
    n=native()
    assert "button[data-testid=\"send-button\"]" in n
    assert "button.click()" in n
    assert 'commit_retry:"canonical_dom_button"' in n
    assert "exact_user_message_found" in n
    assert "requestSubmit()" not in n
