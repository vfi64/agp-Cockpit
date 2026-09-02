from pathlib import Path

CONTENT = Path("chrome_extension/content.js")

def source() -> str:
    return CONTENT.read_text(encoding="utf-8")

def test_structured_response_completion_gate_present():
    s = source()
    assert "AGP_STRUCTURED_RESPONSE_COMPLETION_064_R1" in s
    assert "function parsePureJsonObject(text)" in s
    assert "const structured = parsePureJsonObject(completed);" in s
    assert "ASSISTANT_STRUCTURED_RESPONSE_PENDING" in s
    assert "LIMITS.stablePollsRequired + 5" in s

def test_completion_is_not_committed_before_json_gate():
    s = source()
    parse_pos = s.index("const structured = parsePureJsonObject(completed);")
    commit_pos = s.index("STATE.lastAssistantHash = STATE.candidateHash;", parse_pos)
    assert parse_pos < commit_pos

def test_turn_counting_happens_after_successful_submit():
    s = source()
    fn = s[s.index("async function processCompletedAssistant(text)"):s.index("async function tick()")]
    submit = fn.index("const result = await submitAssistant(text);")
    increment = fn.index("STATE.turns += 1;")
    branch = fn.index('if (result.action !== "continue" || !result.prompt)')
    assert submit < increment < branch
    assert fn.count("STATE.turns += 1;") == 1

def test_old_prompt_based_turn_increment_removed():
    s = source()
    assert "await sendPrompt(result.prompt);\n    STATE.turns += 1;" not in s

def test_live_probe_validation_remains_fail_closed():
    s = source()
    assert "function assertExactLiveProbeWorkOrder(text)" in s
    assert "LIVE probe rejected before local submit" in s
