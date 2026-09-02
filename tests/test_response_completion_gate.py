from pathlib import Path


def test_response_completion_gate_present():
    source = Path(
        "chrome_extension/content.js"
    ).read_text(encoding="utf-8")

    assert "stablePollsRequired: 3" in source
    assert "ASSISTANT_CANDIDATE_CHANGED" in source
    assert "ASSISTANT_CANDIDATE_STABLE" in source
    assert "ASSISTANT_RESPONSE_COMPLETE" in source
    assert "candidateStablePolls" in source
    assert "minAssistantChars: 8" in source


def test_partial_response_not_immediately_submitted():
    source = Path(
        "chrome_extension/content.js"
    ).read_text(encoding="utf-8")

    assert "if (text.length < LIMITS.minAssistantChars)" in source
    assert "STATE.candidateStablePolls < LIMITS.stablePollsRequired" in source
