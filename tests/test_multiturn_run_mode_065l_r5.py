from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "chrome_extension" / "content.js"

def extract_function(source: str, name: str) -> str:
    m = re.search(
        r"\b(?:async\s+)?function\s+" + re.escape(name) + r"\s*\([^)]*\)\s*\{",
        source,
    )
    assert m, f"function {name} not found"
    brace = source.find("{", m.start())
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[m.start():i + 1]
    raise AssertionError(f"unterminated function {name}")

def src() -> str:
    return CONTENT.read_text(encoding="utf-8")

def test_multiturn_live_probe_uses_full_auto():
    block = extract_function(src(), "newMultiTurnLiveProbeMission")
    assert re.search(r'run_mode\s*:\s*["\']FULL_AUTO["\']', block)
    assert not re.search(r'run_mode\s*:\s*["\']SINGLE_STEP["\']', block)

def test_single_live_probe_remains_single_step():
    block = extract_function(src(), "newLiveProbeMission")
    assert re.search(r'run_mode\s*:\s*["\']SINGLE_STEP["\']', block)

def test_multiturn_probe_keeps_exact_read_only_sequence():
    # The exact sequence is defined by the shared MULTITURN_LIVE_PROBE contract,
    # not duplicated inside newMultiTurnLiveProbeMission().
    compact = re.sub(r"\s+", "", src())
    assert '["/usr/bin/git","status","--short"]' in compact
    assert '["/usr/bin/git","branch","--show-current"]' in compact
    assert '["/usr/bin/git","log","-1","--oneline"]' in compact

def test_multiturn_probe_still_has_three_steps():
    # Title and step contract live in the shared probe definition.
    source = src()
    assert "065 LIVE 3-TURN READ-ONLY PROBE" in source
    block = extract_function(source, "newMultiTurnLiveProbeMission")
    assert 'clientEvent("MULTITURN_LIVE_PROBE_MISSION_CREATED", {steps:3})' in block
