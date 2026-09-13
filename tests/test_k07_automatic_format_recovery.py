from pathlib import Path

C = Path("chrome_extension/content.js").read_text()


def test_bounded_automatic_format_repair_is_present():
    assert "AGP_FORMAT_REPAIR_ATTEMPTS" in C
    assert "AGP_MAX_FORMAT_REPAIR_ATTEMPTS = 2" in C
    assert "function formatRepairPrompt(" in C
    assert "FORMAT REPAIR ONLY" in C
    assert "SAME intended work order" in C
    assert "without changing its semantics" in C
    assert "exactly one JSON object and nothing else" in C
    assert "await sendPrompt(formatRepairPrompt(repairAttempt))" in C


def test_format_repair_remains_fail_closed():
    assert "after automatic format repair" in C
    assert "AGP_FORMAT_REPAIR_ATTEMPTS = 0; // valid structured response" in C
    assert "parsePureJsonObject(completed)" in C
    assert "extractSingleWorkOrderJson(completed)" in C


def test_local_llm_is_not_in_the_production_recovery_path():
    section = C[C.index("let AGP_FORMAT_REPAIR_ATTEMPTS"):C.index("async function sendPrompt")]
    assert "ollama" not in section.lower()
    assert "qwen" not in section.lower()
    assert "hermes" not in section.lower()
