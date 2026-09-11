from pathlib import Path
from agp_cockpit.settings import AppSettings, save_settings, load_settings

ROOT=Path(__file__).resolve().parents[1]

def test_settings_authority_defaults_deny_and_round_trip(tmp_path):
    p=tmp_path/"settings.json"
    s=AppSettings()
    assert s.allowed_effects == () and s.allowed_tools == () and s.allow_network is False
    configured=AppSettings(allowed_effects=("E0","E2"),allowed_tools=("python","git"),allow_network=False)
    save_settings(p,configured)
    loaded,_=load_settings(p)
    assert loaded.allowed_effects == ("E0","E2")
    assert loaded.allowed_tools == ("python","git")
    assert loaded.allow_network is False

def test_desktop_and_bridge_cli_construct_local_contract():
    app=(ROOT/"src/agp_cockpit/app.py").read_text()
    bridge=(ROOT/"src/agp_cockpit/bridge_main.py").read_text()
    assert "LocalTaskContract(" in app and "settings.allowed_effects" in app and "settings.allowed_tools" in app
    assert "--allowed-effect" in bridge and "--allowed-tool" in bridge and "LocalTaskContract(" in bridge

def test_http_execute_authorizes_before_effect_and_ignores_remote_authority_fields():
    source=(ROOT/"src/agp_cockpit/core/bridge_server.py").read_text()
    start=source.index('if path == "/v1/protocol/execute":')
    body=source[start:source.index('if path == "/v1/turn":',start)]
    assert body.index("durable.action_authorized(authorization_payload)") < body.index("execute_direct_action(")
    assert "ACTION_NOT_AUTHORIZED_BY_LOCAL_TASK_CONTRACT" in body
    assert 'action.work_order.get("allowed_effects")' not in body
    assert 'action.work_order.get("allowed_tools")' not in body
    assert "durable.store.task_authority(durable.task_id)" in body


def test_executor_secondary_policy_receives_local_authority():
    execution=(ROOT/'src/agp_cockpit/core/bridge_execution.py').read_text()
    protocol=(ROOT/'src/agp_cockpit/core/protocol_execution_v1.py').read_text()
    server=(ROOT/'src/agp_cockpit/core/bridge_server.py').read_text()
    assert 'allowed_tools=allowed_tools' in execution and 'allow_network=allow_network' in execution
    assert 'allowed_tools=allowed_tools' in protocol and 'allow_network=allow_network' in protocol
    assert 'authority_order = parse_work_order_json' in server
    assert 'allowed_tools=frozenset(' in server and 'allow_network=bool(' in server
