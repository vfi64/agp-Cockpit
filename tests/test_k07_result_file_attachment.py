from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome_extension" / "result_file_attachment.js"
BACKGROUND = ROOT / "chrome_extension" / "background.js"

def test_background_loads_attachment_seam():
    assert 'importScripts("result_file_attachment.js");' in BACKGROUND.read_text()

def test_attachment_source_uses_cdp_file_input_without_composer_payload_fallback():
    text = SRC.read_text()
    assert "DOM.setFileInputFiles" in text
    assert 'input[type="file"]' in text
    assert "Runtime.evaluate" in text
    assert "Runtime.callFunctionOn" in text
    assert "AGPResultFileAttachment" in text
    assert "RESULT_FILE_ATTACHED" in text
    assert "prompt-textarea" not in text
    assert "JSON.stringify" not in text

def test_attachment_source_fails_loudly_when_file_input_missing():
    text = SRC.read_text()
    assert 'throw new Error("ChatGPT file input not found")' in text
    assert 'throw new Error("absolute local file path required")' in text
