from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_existing_result_attachment_authority_is_reused():
    b=(ROOT/"chrome_extension/background.js").read_text()
    c=(ROOT/"chrome_extension/content.js").read_text() +(ROOT/"chrome_extension/cockpit_ingress.js").read_text()   # AGP_INGRESS_MODULE_V1: content.js + its ingress module
    assert "agpSubmitFileLoopContinuation(tabId, absolutePath, outputPath, continuationPrompt, message.cycle_id, message.result_sha256)" in b
    assert 'message.type !== "AGP_K07_RESULT_CONTINUATION"' in b
    assert "AGPResultFileAttachment.attachResultFiles" in b
    assert 'type: "AGP_K07_SEND_PROMPT"' in b
    assert "chrome.tabs.sendMessage(tabId" in b
    assert 'message.type === "AGP_K07_SEND_PROMPT"' in c
    assert "sendResponse({ok:true, stage:\"PROMPT_SENT\"})" in c
    assert 'type:"AGP_K07_RESULT_CONTINUATION"' in c
    assert "result_file:result.result_file" in c
    assert "output_file:result.output_file || null" in c
    assert "prompt:result.prompt" in c
    # AGP_K07_DELIVERY_STATE_V1: only confirmed deliveries suppress replay.
    assert "if (result.replayed === true && result.delivery_pending !== true)" in c
    assert "if (result.held === true)" in c
    assert "AGP_K07_ADVANCE_STEP_AFTER_DELIVERY_V1" in c
    assert '"/v1/file-loop/delivery-ack"' in c
    assert "async function agpSubmitFileLoopContinuation(tabId, absolutePath, outputPath, continuationPrompt, cycleId, resultSha256)" in b
    assert "message.cycle_id, message.result_sha256" in b
    assert "cycle_id:cycleId || null" in b
    assert "identical prompt loop detected" not in c
