from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "chrome_extension" / "content.js"

def src():
    return SRC.read_text()

def test_r8_has_user_message_snapshot_helper():
    s = src()
    assert "function visibleUserMessages()" in s
    assert 'data-message-author-role="user"' in s

def test_r8_waits_for_new_matching_user_message():
    s = src()
    start = s.index("async function waitForSentUserMessage(")
    end = s.index(") {", start)
    signature = " ".join(s[start:end + 3].split())
    assert signature.startswith("async function waitForSentUserMessage(")
    assert "prompt" in signature
    assert "beforeMessages" in signature
    assert 'beforeAssistantText=""' in signature
    assert 'beforeComposerText=""' in signature
    assert "beforeGenerationActive=false" in signature
    assert "after.length > beforeCount" in s
    assert "const expected = normalizeObservedMessageText(prompt);" in s
    assert "const newest = normalizeObservedMessageText(after[after.length - 1]);" in s
    assert "if (newest === expected)" in s

def test_r8_fails_closed_if_send_is_not_confirmed():
    s = src()
    assert 'STATE.lastEvent = "SEND_UNCONFIRMED"' in s
    assert 'throw new Error("SEND_UNCONFIRMED: expected user message did not appear")' in s

def test_r8_only_marks_prompt_sent_after_confirmation():
    s = src()
    confirmed = s.index("const acknowledgement = await waitForSentUserMessage(")
    prompt_sent = s.index('STATE.lastEvent = "PROMPT_SENT";', confirmed)
    assert prompt_sent > confirmed

def test_r8_preserves_multiturn_full_auto_contract():
    s = src()
    assert 'run_mode:"FULL_AUTO"' in s
    assert "065 LIVE 3-TURN READ-ONLY PROBE" in s

def test_r8_preserves_single_turn_single_step_contract():
    s = src()
    assert 'run_mode:"SINGLE_STEP"' in s
