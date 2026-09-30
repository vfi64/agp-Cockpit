from pathlib import Path

CONTENT = Path(__file__).parents[1] / "chrome_extension" / "content.js"

def test_k07_assistant_baseline_prefers_message_identity_over_node_count():
    text = CONTENT.read_text(encoding="utf-8")
    assert 'assistantBaselineMessageId: ""' in text
    assert "assistantBaselineMessageIds: []" in text
    assert "function lastAssistantMessageId()" in text
    assert "function assistantBaselineIds()" in text
    assert "assistantBaselineIds().has(newestMessageId)" in text
    assert "!STATE.assistantBaselineMessageId &&" in text
    assert "nodes.length <= STATE.assistantBaselineCount" in text

def test_k07_all_assistant_baseline_captures_include_message_identity():
    text = CONTENT.read_text(encoding="utf-8")
    assert text.count("captureAssistantBaseline();") >= 3
    # AGP_K07_BASELINE_BEFORE_SEND_V1: snapshot/apply split keeps identity.
    assert "STATE.assistantBaselineMessageIds = baseline.ids" in text
    assert "lastId:lastAssistantMessageId()" in text
    assert "STATE.assistantBaselineMessageId = baseline.lastId" in text
