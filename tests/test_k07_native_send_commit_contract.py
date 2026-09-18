from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND = (ROOT / "chrome_extension" / "background.js").read_text()
NATIVE = (ROOT / "chrome_extension" / "browser_native_transport.js").read_text()
CONTENT = (ROOT / "chrome_extension" / "content.js").read_text()

def test_cdp_verifies_inserted_text_before_submit():
    assert '"Input.insertText"' in BACKGROUND
    assert 'stage:"INSERT_NOT_VERIFIED"' in BACKGROUND
    assert "normalize(inserted && inserted.value) !== normalize(text)" in BACKGROUND
    assert 'modelVerification.stage === "COMPOSER_MODEL_VERIFIED"' in BACKGROUND
    assert 'stage:"COMPOSER_MODEL_NOT_VERIFIED"' in BACKGROUND
    assert "active === composer" in BACKGROUND

def test_cdp_requires_exact_persistent_user_turn_commit():
    assert 'stage:"USER_TURN_COMMITTED"' in BACKGROUND
    assert '"USER_TURN_INDETERMINATE"' in BACKGROUND
    assert '"USER_TURN_NOT_COMMITTED"' in BACKGROUND
    assert "exact_user_message_found" in BACKGROUND
    assert "USER_TURN_COMMITTED" in NATIVE

def test_native_module_allows_indeterminate_but_rejects_uncommitted_stage():
    assert 'response.stage === "USER_TURN_INDETERMINATE"' in NATIVE
    assert 'response.stage !== "USER_TURN_COMMITTED"' in NATIVE
    assert "native transport uncommitted stage" in NATIVE


def test_native_model_failure_has_bounded_refocus_retry_and_reconciliation():
    start = CONTENT.index("async function sendPromptNative(prompt)")
    end = CONTENT.index("async function sendPrompt(prompt)", start)
    fn = CONTENT[start:end]
    assert "attempt <= 2" in fn
    assert 'COMPOSER_MODEL_RECOVERY_EXHAUSTED' in fn
    assert "waitForSentUserMessage" in fn
    assert 'via:"reconciliation"' in fn

def test_generation_started_is_telemetry_only():
    start = CONTENT.index("async function waitForSentUserMessage(")
    end = CONTENT.index("// AGP_BROWSER_SENDER_TRANSPORT_STATE_MACHINE_092", start)
    fn = CONTENT[start:end]
    assert 'via:"generation_started"' not in fn
    assert "SEND_GENERATION_STARTED_OBSERVED" in fn

def test_assistant_activity_is_telemetry_only():
    start = CONTENT.index("async function waitForSentUserMessage(")
    end = CONTENT.index("// AGP_BROWSER_SENDER_TRANSPORT_STATE_MACHINE_092", start)
    fn = CONTENT[start:end]
    assert 'via:"assistant_activity"' not in fn
    assert "SEND_ASSISTANT_ACTIVITY_OBSERVED" in fn

def test_native_acceptance_is_only_user_message_commit():
    start = CONTENT.index("async function sendPromptNative(prompt)")
    end = CONTENT.index("async function sendPrompt(prompt)", start)
    fn = CONTENT[start:end]
    assert 'via:"user_message"' in fn
    assert "NATIVE_USER_TURN_COMMITTED" in fn
    assert 'native_stage:"USER_TURN_COMMITTED"' in fn
