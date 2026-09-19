import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "chrome_extension" / "content.js").read_text(encoding="utf-8")

def extract_function(text: str, name: str) -> str:
    m = re.search(rf'(?:(?:async)\s+)?function\s+{re.escape(name)}\s*\(', text)
    assert m, f"{name} missing"
    brace = text.find("{", m.end())
    assert brace >= 0
    depth = 0
    quote = None
    escaped = False
    for i in range(brace, len(text)):
        ch = text[i]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i+1]
    raise AssertionError(f"{name} unterminated")

def test_e7_generation_ack_requires_fresh_edge():
    block = extract_function(SRC, "waitForSentUserMessage")
    assert "generationNow &&" in block
    assert "!beforeGenerationActive" in block
    assert "!generationStartedObserved" in block
    assert "SEND_GENERATION_STARTED_OBSERVED" in block
    assert "generation_started_observed:generationStartedObserved" in block
    assert 'via:"generation_active"' not in block

def test_e7_other_decisive_ack_paths_remain():
    block = extract_function(SRC, "waitForSentUserMessage")
    assert 'via:"user_message"' in block
    assert "SEND_ASSISTANT_ACTIVITY_OBSERVED" in block
    assert "authoritative_acceptance:false" in block
    assert 'confirmed:false' in block
    assert 'via:"timeout"' in block

def test_e7_composer_mutation_remains_provisional():
    block = extract_function(SRC, "waitForSentUserMessage")
    assert 'provisionalComposerEvidence' in block
    assert 'return {confirmed:true, via:"composer_cleared"}' not in block
    assert 'return {confirmed:true, via:"composer_changed"}' not in block
