from pathlib import Path


def test_server_result_replay_contract():
    text=Path('src/agp_cockpit/core/bridge_server.py').read_text()
    assert 'self.protocol_v1_results: dict[str, str] = {}' in text
    assert 'cached = protocol_v1_results.get(action.action_id)' in text
    assert '"decision": "REPLAYED"' in text
    assert 'protocol_v1_results[action.action_id] = frame' in text
    assert 'duplicate action has no completed result; automatic replay forbidden' in text

def test_browser_accepts_replayed_result():
    # AGP_LEGACY_PATHS_REMOVED_V1: phase7_single_round.js is gone; the live client is submitAssistant.
    text=Path('chrome_extension/content.js').read_text()
    assert '["EXECUTED","REPLAYED"].includes(String(result.decision || ""))' in text
