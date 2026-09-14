from pathlib import Path

C = Path("chrome_extension/content.js").read_text()


def test_unique_work_order_extractor_is_present_and_bounded():
    assert "function extractSingleWorkOrderJson(text)" in C
    assert "const required = [\"kind\", \"cwd\", \"argv\", \"timeout_seconds\", \"label\"]" in C
    assert "candidates.length !== 1" in C
    assert "new Set(candidates.map" in C


def test_tick_uses_extracted_json_text_for_processing():
    assert "const extracted = extractSingleWorkOrderJson(completed);" in C
    assert "const structured = extracted ? extracted.value : pureStructured;" in C
    assert "const completedForProcessing = extracted ? extracted.text : completed;" in C
    assert "await processCompletedAssistant(completedForProcessing, runGeneration);" in C


def test_fail_closed_behavior_is_retained():
    assert "assistant response stayed stable but is not a complete pure JSON object after automatic format repair" in C
    assert "return null;" in C
