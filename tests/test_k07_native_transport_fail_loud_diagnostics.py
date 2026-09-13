from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
NATIVE=(ROOT/'chrome_extension/browser_native_transport.js').read_text()
BACKGROUND=(ROOT/'chrome_extension/background.js').read_text()

def test_native_transport_fail_loud_response_payload():
    assert 'native transport rejected: ${JSON.stringify(response || null)}' in NATIVE

def test_runtime_messaging_error_is_preserved():
    assert 'runtime_message_error' in NATIVE

def test_background_marks_native_exception_stage():
    assert 'stage:"NATIVE_TRANSPORT_EXCEPTION"' in BACKGROUND
    assert 'error:String(error && error.message ? error.message : error)' in BACKGROUND
