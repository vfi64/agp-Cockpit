from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def test_bridge_does_not_self_grant_e3_for_kit_work_order():
    s=(ROOT/'src/agp_cockpit/core/bridge_server.py').read_text()
    assert '\"effect\": \"E3\" if authority_order.kind == \"kit\" else \"E2\"' not in s
    assert '\"effect\": \"E2\"' in s
    assert 'durable.action_authorized(authorization_payload)' in s
