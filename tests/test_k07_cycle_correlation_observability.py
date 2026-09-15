from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / 'src/agp_cockpit/core/bridge_server.py').read_text(encoding='utf-8')

def test_cycle_identity_joins_command_and_result_observation():
    assert 'cycle_id = "k07-" + _k07_cycle_hash.sha256(' in BRIDGE
    assert '"K07_COMMAND_ACCEPTED"' in BRIDGE
    assert '"K07_RESULT_BUNDLE_CREATED"' in BRIDGE
    assert '"cycle_id": cycle_id' in BRIDGE
    assert '"result_sha256": result_sha256' in BRIDGE

def test_existing_execution_and_task_authorities_remain():
    assert 'outcome = consume_command_file(' in BRIDGE
    assert 'DurableTaskController' in BRIDGE
    assert 'command-file execution produced no return bundle' in BRIDGE

def test_browser_result_transport_preserves_existing_cycle_correlation():
    content = Path('chrome_extension/content.js').read_text()
    background = Path('chrome_extension/background.js').read_text()
    assert 'cycle_id:result.cycle_id || null' in content
    assert 'result_sha256:result.result_sha256 || null' in content
    assert 'event:"BROWSER_RESULT_ATTACHED"' in background
    assert 'event:"CONTINUATION_SENT"' in background
    assert 'cycle_id:message.cycle_id || null' in background
