"""r6 (2026-10-05): mission start from a new ChatGPT chat.

Live: the start page renders three composer forms (two 0x0). The Kit command
digest went to the first file input of the document (invisible form 0) and the
bounded native retry refused its own draft ("requires an empty composer").
Behavior is proven on real Chromium in
tests/e2e/test_r6_new_chat_composer_attachment.spec.js; these checks pin the
source-level contract.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "chrome_extension"
ATTACH = (EXT / "result_file_attachment.js").read_text(encoding="utf-8")
EVIDENCE = (EXT / "native_message_evidence.js").read_text(encoding="utf-8")
CONTENT = (EXT / "content.js").read_text(encoding="utf-8")


def _resolver() -> str:
    start = EVIDENCE.index("function agpResolveComposer()")
    end = EVIDENCE.index("function agpNativeMessageSnapshot", start)
    return EVIDENCE[start:end]


def test_resolver_rejects_composers_inside_invisible_forms():
    fn = _resolver()
    assert "AGP_COMPOSER_VISIBLE_FORM_V1" in fn
    assert 'el.closest("form")' in fn
    assert "formRect.width > 0 && formRect.height > 0" in fn


def test_attachment_file_input_is_bound_to_the_resolved_composer_form():
    assert "AGP_RESULT_ATTACHMENT_COMPOSER_BOUND_V1" in ATTACH
    assert "globalThis.agpResolveComposer" in ATTACH
    assert 'form.querySelectorAll(\'input[type="file"]\')' in ATTACH
    # No document-wide file-input selection and no stale #prompt-textarea anchor.
    assert "document.querySelectorAll('input[type=\"file\"]')" not in ATTACH
    assert "#prompt-textarea" not in ATTACH
    assert 'throw new Error("ChatGPT composer resolver unavailable")' in ATTACH


def test_presence_evidence_uses_the_same_composer_identity():
    assert "presenceExpression(expectedNames, resolverSource)" in ATTACH
    assert "const composer = (${resolverSource})();" in ATTACH


def test_native_retry_clears_only_its_own_draft_before_attempt_two():
    start = CONTENT.index("async function clearOwnedDraftBeforeRetry(")
    end = CONTENT.index("async function sendPromptNative(prompt)", start)
    helper = CONTENT[start:end]
    assert "AGP_NATIVE_RETRY_OWNED_DRAFT_V1" in CONTENT[start - 800:start]
    assert "staged === expected" in helper
    assert "AGP_COMMIT_MARKER_PATTERN.test(marker)" in helper
    assert "foreign composer content; refusing to overwrite" in helper
    assert "could not clear its own draft" in helper
    assert "NATIVE_RETRY_OWNED_DRAFT_CLEARED" in helper

    fn_start = CONTENT.index("async function sendPromptNative(prompt)")
    fn = CONTENT[fn_start:CONTENT.index("async function sendPrompt(prompt)", fn_start)]
    retry = "if (attempt > 1) await clearOwnedDraftBeforeRetry(prompt, commitMarker, attempt);"
    assert retry in fn
    assert fn.index(retry) < fn.index("nativeTransport.submit(prompt, {attempt, commitMarker})")


BACKGROUND = (EXT / "background.js").read_text(encoding="utf-8")


def test_trusted_enter_refocuses_the_resolved_composer_first():
    assert "function agpRefocusComposerForSubmit(resolveComposer)" in EVIDENCE
    primary = BACKGROUND.index('event:"PRIMARY_ENTER_BEFORE"')
    retry = BACKGROUND.index('event:"RETRY_ENTER_BEFORE"')
    assert BACKGROUND.rindex("await refocusForSubmit()", 0, primary) < primary
    assert BACKGROUND.rindex("await refocusForSubmit()", 0, retry) < retry
    assert "focus_before_enter:focusBeforeEnter" in BACKGROUND
    assert "focus_before_enter:focusBeforeRetry" in BACKGROUND


def test_dom_send_fallback_uses_the_composer_form_button():
    assert "function agpComposerSendButton(resolveComposer)" in EVIDENCE
    start = BACKGROUND.index("AGP_SUBMIT_FOCUS_AND_FORM_BUTTON_V1: the control is the send button")
    block = BACKGROUND[start:BACKGROUND.index('event:"DOM_SEND_FALLBACK"', start)]
    assert "(${agpComposerSendButton.toString()})(${agpResolveComposer.toString()})" in block
    assert "document.querySelector('button[data-testid=\"send-button\"]')" not in block
