from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_existing_result_attachment_authority_is_reused():
    b=(ROOT/"chrome_extension/background.js").read_text()
    c=(ROOT/"chrome_extension/content.js").read_text()
    assert "agpSubmitFileLoopContinuation(tabId, absolutePath, message.cycle_id, message.result_sha256)" in b
    assert 'message.type !== "AGP_K07_RESULT_CONTINUATION"' in b
    assert "AGPResultFileAttachment.attachResultFile" in b
    assert 'type: "AGP_K07_SEND_PROMPT"' in b
    assert "chrome.tabs.sendMessage(tabId" in b
    assert 'message.type === "AGP_K07_SEND_PROMPT"' in c
    assert "sendResponse({ok:true, stage:\"PROMPT_SENT\"})" in c
    assert 'type:"AGP_K07_RESULT_CONTINUATION"' in c
    assert "result_file:result.result_file" in c
    assert "if (result.replayed === true)" in c
    assert "async function agpSubmitFileLoopContinuation(tabId, absolutePath, cycleId, resultSha256)" in b
    assert "message.cycle_id, message.result_sha256" in b
    assert "cycle_id:cycleId || null" in b
    assert "identical prompt loop detected" not in c
