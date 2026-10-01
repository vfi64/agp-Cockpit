from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
C = (ROOT / "chrome_extension/content.js").read_text()

def test_state_has_generation_and_processor_guard():
    assert "runGeneration: 0" in C
    assert "processingAssistant: false" in C

def test_stop_invalidates_before_reset():
    block = C[C.index('function stop(reason, event="AUTO_STOPPED", operatorStop=true)'):C.index('function missionBootstrapPrompt')]
    assert block.index("STATE.runGeneration += 1") < block.index("STATE.running = false")
    assert "PENDING_SEND_TRANSPORT = null" in block
    assert "AGP_FORMAT_REPAIR_ATTEMPTS = 0" in block

def test_turn_accounting_is_generation_fenced():
    start = C.index("async function processCompletedAssistant")
    block = C[start:C.index("function newAssistantTextAfterBaseline", start)]
    assert "processCompletedAssistant(text, runGeneration)" in block
    assert "STATE.runGeneration !== runGeneration" in block
    assert block.index("STATE.runGeneration !== runGeneration") < block.index("STATE.turns += 1")

def test_format_repair_rebaselines_and_rearms():
    start = C.index('STATE.lastEvent = "ASSISTANT_FORMAT_REPAIR"')
    block = C[start:start + 1800]
    assert "captureAssistantBaseline()" in block
    assert block.index("captureAssistantBaseline()") < block.index("await sendPrompt(formatRepairPrompt")
    assert "STATE.waitingForAssistant = true" in block
    assert "STATE.runGeneration !== repairGeneration" in block

def test_completed_assistant_processing_is_serialized():
    assert "if (STATE.processingAssistant)" in C
    assert "STATE.processingAssistant = true" in C
    assert "await processCompletedAssistant(completedForProcessing, runGeneration)" in C

def test_start_creates_fresh_epoch_and_resets_transient_state():
    start = C.index("async function startAuto()")
    block = C[start:start + 3500]
    assert "STATE.runGeneration += 1" in block
    assert "const runGeneration = STATE.runGeneration" in block
    assert "PENDING_SEND_TRANSPORT = null" in block
    assert "AGP_FORMAT_REPAIR_ATTEMPTS = 0" in block
    assert "STATE.processingAssistant = false" in block
    assert "STATE.waitingForAssistant = false" in block
