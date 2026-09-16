from pathlib import Path

C = Path("chrome_extension/content.js").read_text()

def _fn():
    a=C.index("function newAssistantTextAfterBaseline()")
    b=C.index("async function tick()",a)
    return C[a:b]

def test_1128_generation_fence_records_baseline_text():
    assert 'assistantBaselineText: ""' in C
    assert C.count("STATE.assistantBaselineText = normalizeObservedMessageText(lastAssistantText());") >= 4

def test_1128_virtualized_same_count_changed_text_is_not_suppressed():
    fn=_fn()
    assert "normalizedNewestText === STATE.assistantBaselineText" in fn
    assert "nodes.length <= STATE.assistantBaselineCount" in fn
    assert fn.index("normalizedNewestText === STATE.assistantBaselineText") < fn.index("return newestText;")

def test_1128_message_id_remains_primary_generation_fence():
    fn=_fn()
    assert "newestMessageId === STATE.assistantBaselineMessageId" in fn
    assert fn.index("newestMessageId === STATE.assistantBaselineMessageId") < fn.index("normalizedNewestText === STATE.assistantBaselineText")
