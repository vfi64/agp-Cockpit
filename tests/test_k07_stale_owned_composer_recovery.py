from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")

def native_fn():
    start = TEXT.index("async function sendPromptNative(prompt)")
    end = TEXT.index("async function sendPrompt(prompt)", start)
    return TEXT[start:end]

def test_foreign_nonempty_composer_still_fails_closed():
    fn = native_fn()
    assert "stagedComposerText !== expectedPromptText" in fn
    assert "non-empty foreign composer content; refusing to overwrite" in fn

def test_exact_current_prompt_is_only_auto_recoverable_draft():
    fn = native_fn()
    assert "NATIVE_STALE_OWNED_COMPOSER_RECOVERED" in fn
    assert 'ownership:"exact_current_prompt"' in fn
    assert 'setComposerText(staleOwnedComposer, "")' in fn

def test_failed_command_recovery_draft_is_owned_by_cockpit():
    fn = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")
    assert "The attached local execution evidence reports a FAILED command-file step." in fn

def test_cleanup_must_be_observed_before_native_submit_continues():
    fn = native_fn()
    assert "could not clear exact stale Cockpit-owned draft" in fn
    assert "cleanupDeadline" in fn
    assert fn.index("NATIVE_STALE_OWNED_COMPOSER_RECOVERED") < fn.index("nativeTransport.submit(prompt, {attempt, commitMarker})")

def test_old_blanket_empty_composer_error_is_removed():
    fn = native_fn()
    assert "browser-native transport requires an empty composer before submit" not in fn
