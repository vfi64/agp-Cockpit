from pathlib import Path

C = Path("chrome_extension/content.js").read_text()


def test_structured_assistant_extractor_prefers_semantic_json_payloads():
    assert "AGP_K07_STRUCTURED_ASSISTANT_EXTRACTION_738" in C
    assert 'assistant.querySelectorAll("pre code, code")' in C
    assert "uniqueCodeCandidates.length === 1" in C
    assert 'assistant.querySelectorAll("pre")' in C
    assert "uniquePreCandidates.length === 1" in C
    assert "rendered.matchAll" in C
    assert "uniqueFencedCandidates.length === 1" in C
    assert "pureJsonObjectCandidate" in C


def test_fail_closed_fallback_and_validation_retained():
    assert "return rendered;" in C
    assert "parsePureJsonObject" in C
    assert "JSON.parse" in C
    assert "!Array.isArray" in C
    assert "assistant response stayed stable but is not a complete pure JSON object" in C
