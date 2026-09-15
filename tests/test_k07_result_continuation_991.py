from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_existing_result_attachment_authority_is_reused():
    b=(ROOT/"chrome_extension/background.js").read_text()
    c=(ROOT/"chrome_extension/content.js").read_text()
    assert "agpSubmitFileLoopContinuation(tabId, absolutePath)" in b
    assert 'message.type !== "AGP_K07_RESULT_CONTINUATION"' in b
    assert "AGPResultFileAttachment.attachResultFile" in b
    assert "sendPromptToChatGPT(tabId, continuation)" in b
    assert 'type:"AGP_K07_RESULT_CONTINUATION"' in c
    assert "result_file:result.result_file" in c
