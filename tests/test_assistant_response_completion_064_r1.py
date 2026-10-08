from pathlib import Path

CONTENT = Path("chrome_extension/content.js")

def source() -> str:
    return CONTENT.read_text(encoding="utf-8")

def test_structured_response_completion_gate_present():
    s = source()
    assert "AGP_STRUCTURED_RESPONSE_COMPLETION_064_R1" in s
    assert "function parsePureJsonObject(text)" in s
    assert "const pureStructured = parsePureJsonObject(completed);" in s
    assert "const extracted = extractSingleWorkOrderJson(completed);" in s
    assert "const structured = extracted ? extracted.value : pureStructured;" in s
    assert "ASSISTANT_STRUCTURED_RESPONSE_PENDING" in s
    assert "LIMITS.stablePollsRequired + 5" in s

def test_completion_is_not_committed_before_json_gate():
    s = source()
    parse_pos = s.index("const extracted = extractSingleWorkOrderJson(completed);")
    commit_pos = s.index("STATE.lastAssistantHash = STATE.candidateHash;", parse_pos)
    assert parse_pos < commit_pos

def test_turn_counting_happens_after_successful_submit():
    s = source()
    fn = s[s.index("async function processCompletedAssistant(text, runGeneration)"):s.index("async function tick()")]
    command_submit = fn.index("await submitAssistantCommandFile(runGeneration);")
    # A re-delivered replay is not a new executed turn.
    command_increment = fn.index("STATE.turns += redelivered ? 0 : 1;", command_submit)
    legacy_submit = fn.index("const result = await submitAssistant(text);")
    legacy_increment = fn.index("STATE.turns += 1;", legacy_submit)
    prompt_increment = fn.rindex("STATE.turns += 1;")
    legacy_branch = fn.index('if (result.action !== "continue" || !result.prompt)', legacy_submit)
    prompt_send = fn.index("await sendPrompt(result.prompt);", legacy_submit)
    assert command_submit < command_increment < legacy_submit
    assert legacy_submit < legacy_branch < legacy_increment
    assert prompt_send < prompt_increment
    # AGP_CORRECTABLE_REJECTION_V1: the correction prompt is a turn too, counted
    # only after its send succeeded.
    correction_send = fn.index("await sendPrompt(String(commandResult.prompt));")
    correction_increment = fn.index("STATE.turns += 1;", correction_send)
    assert command_submit < correction_send < correction_increment < command_increment
    assert fn.count("STATE.turns += 1;") == 3

def test_old_prompt_based_turn_increment_removed():
    s = source()
    assert "await sendPrompt(result.prompt);\n    STATE.turns += 1;" not in s

def test_k07_requires_new_assistant_node_after_submit() -> None:
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "chrome_extension" / "content.js").read_text(encoding="utf-8")
    assert "function assistantMessageNodes()" in source
    assert "function assistantBaselineIds()" in source
    assert "function captureAssistantBaseline()" in source
    assert "STATE.assistantBaselineMessageIds = baseline.ids" in source
    assert "function newAssistantTextAfterBaseline()" in source
    assert "nodes.length <= STATE.assistantBaselineCount" in source
    tick = source[source.index("async function tick()"):]
    assert "const text = newAssistantTextAfterBaseline();" in tick
