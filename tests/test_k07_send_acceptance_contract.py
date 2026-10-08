from pathlib import Path

SEND_JS = (Path(__file__).resolve().parents[1] / "chrome_extension" / "cockpit_send.js").read_text(encoding="utf-8")  # AGP_SEND_MODULE_V1

SOURCE = (
    Path(__file__).resolve().parents[1] / "chrome_extension" / "content.js"
).read_text(encoding="utf-8") + "\n" + SEND_JS

def _wait_fn():
    start = SOURCE.index("async function waitForSentUserMessage(")
    end = SOURCE.index("// AGP_BROWSER_SENDER_TRANSPORT_STATE_MACHINE_092", start)
    return SOURCE[start:end]

def test_generation_started_is_not_authoritative_send_acceptance():
    fn = _wait_fn()
    assert 'via:"generation_started"' not in fn
    assert "SEND_GENERATION_STARTED_OBSERVED" in fn
    assert "authoritative_acceptance:false" in fn

def test_exact_new_user_message_remains_authoritative_acceptance():
    fn = _wait_fn()
    assert 'return {confirmed:true, via:"user_message"};' in fn

def test_assistant_activity_is_diagnostic_only_not_send_acceptance():
    fn = _wait_fn()
    assert 'via:"assistant_activity"' not in fn
    assert "SEND_ASSISTANT_ACTIVITY_OBSERVED" in fn
    assert "authoritative_acceptance:false" in fn

def test_timeout_preserves_generation_started_as_diagnostic_only():
    fn = _wait_fn()
    assert "generation_started_observed:generationStartedObserved" in fn
    assert "confirmed:false" in fn

def test_indeterminate_transport_records_generation_started_without_accepting():
    assert "generation_started_observed:Boolean(" in SOURCE
    assert "SEND_TRANSPORT.INDETERMINATE" in SOURCE
