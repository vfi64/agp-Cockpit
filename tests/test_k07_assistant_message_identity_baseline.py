from pathlib import Path

CONTENT = Path(__file__).parents[1] / "chrome_extension" / "content.js"

def test_k07_assistant_baseline_prefers_message_identity_over_node_count():
    text = CONTENT.read_text(encoding="utf-8")
    assert 'assistantBaselineMessageId: ""' in text
    assert "function lastAssistantMessageId()" in text
    assert "newestMessageId === STATE.assistantBaselineMessageId" in text
    assert "!STATE.assistantBaselineMessageId &&" in text
    assert "nodes.length <= STATE.assistantBaselineCount" in text

def test_k07_all_assistant_baseline_captures_include_message_identity():
    text = CONTENT.read_text(encoding="utf-8")
    count_assign = "STATE.assistantBaselineCount = assistantMessageNodes().length;"
    id_assign = "STATE.assistantBaselineMessageId = lastAssistantMessageId();"
    count_captures = text.count(count_assign)
    identity_captures = text.count(id_assign)
    assert count_captures >= 3
    assert identity_captures == count_captures
