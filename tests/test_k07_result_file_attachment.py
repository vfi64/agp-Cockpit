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
    assert 'debugger.attach(target, "1.3")' in text
    assert 'debugger.detach(target)' in text
    assert "AGPResultFileAttachment" in text
    assert "RESULT_FILE_ATTACHED" in text
    assert "attachResultFiles" in text
    # The composer is only observed for attachment evidence; the seam never
    # writes a payload into it (no text insertion fallback).
    for forbidden in ("insertText", "execCommand", ".value =", "textContent =", "innerText ="):
        assert forbidden not in text
    # AGP_K07_RESULT_ATTACHMENT_EVIDENCE_V2: no synthetic re-dispatch after
    # DOM.setFileInputFiles; behavior is proven in
    # tests/e2e/test_k07_result_attachment_evidence.spec.js on real Chromium.
    assert "dispatchEvent" not in text
    assert "AGP_K07_RESULT_ATTACHMENT_EVIDENCE_V2" in text

def test_attachment_source_fails_loudly_when_file_input_missing():
    text = SRC.read_text()
    assert 'throw new Error("ChatGPT file input not found")' in text
    assert 'throw new Error("absolute local file paths required")' in text
