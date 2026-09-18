from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / 'src/agp_cockpit/core/bridge_server.py').read_text(encoding='utf-8')

def test_cycle_identity_joins_command_and_result_observation():
    assert 'cycle_id = "k07-" + _k07_cycle_hash.sha256(' in BRIDGE
    assert '"K07_COMMAND_ACCEPTED"' in BRIDGE
    assert '"K07_RESULT_BUNDLE_CREATED"' in BRIDGE
    assert '"cycle_id": cycle_id' in BRIDGE
    assert '"result_sha256": result_sha256' in BRIDGE
    assert '"output_file": str(output_path)' in BRIDGE
    assert '"output_sha256": output_sha256' in BRIDGE
    assert '"result_validation": result_validation' in BRIDGE
    assert '"result_status": parsed_result.get("status")' in BRIDGE

def test_existing_execution_and_task_authorities_remain():
    assert 'outcome = consume_command_file(' in BRIDGE
    assert 'DurableTaskController' in BRIDGE
    assert 'command-file execution produced no return bundle' in BRIDGE

def test_browser_result_transport_preserves_existing_cycle_correlation():
    content = Path('chrome_extension/content.js').read_text()
    background = Path('chrome_extension/background.js').read_text()
    assert 'cycle_id:result.cycle_id || null' in content
    assert 'result_sha256:result.result_sha256 || null' in content
    assert 'event:"BROWSER_RESULT_EVIDENCE_ATTACHED"' in background
    assert 'event:"CONTINUATION_SENT"' in background
    assert 'prompt:result.prompt' in content
    assert 'const continuationPrompt = String(message.prompt || "").trim();' in background
    assert 'prompt: continuationPrompt' in background
    assert 'cycle_id:cycleId || null' in background

def test_failed_command_turn_is_visible_without_claiming_completion():
    content = Path('chrome_extension/content.js').read_text()
    assert 'K07_COMMAND_FILE_TURN_FAILED' in content
    assert 'commandResult.result_status === "failed"' in content
    assert 'local command execution failed; recovery requested' in content
