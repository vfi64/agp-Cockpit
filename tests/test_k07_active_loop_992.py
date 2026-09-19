from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def completed_assistant_source():
    s=(ROOT/"chrome_extension/content.js").read_text()
    fn=s[s.index("async function processCompletedAssistant(text, runGeneration)"):]
    return fn[:fn.index("\n  }\n")+5]

def test_command_file_branch_precedes_existing_legacy_submit_path():
    fn=completed_assistant_source()
    assert "AGP_K07_COMMAND_FILE_ACTIVE_BRANCH_992" in fn
    assert "assistantPythonAttachmentCandidates()" in fn
    assert "await submitAssistantCommandFile()" in fn
    assert "STATE.runGeneration !== runGeneration" in fn
    assert 'STATE.lastEvent = failed ? "K07_COMMAND_FILE_TURN_FAILED" : "K07_COMMAND_FILE_TURN_COMPLETE"' in fn
    assert fn.index("await submitAssistantCommandFile()") < fn.index("await submitAssistant(text)")

def test_existing_legacy_submit_path_remains_for_compatibility():
    fn=completed_assistant_source()
    assert "const result = await submitAssistant(text);" in fn
    assert 'STATE.lastEvent = "PROMPT_SENT"' in fn
