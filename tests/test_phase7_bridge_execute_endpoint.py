from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
S=(ROOT/"src/agp_cockpit/core/bridge_server.py").read_text()
def body():
    a=S.index('if path == "/v1/protocol/execute":')
    b=S.index('if path == "/v1/turn":',a)
    return S[a:b]
def test_execute_endpoint_registers_before_execution_and_returns_frame():
    x=body()
    assert x.index("protocol_v1_actions.register(action)") < x.index("execute_direct_action(")
    assert '"result_frame": frame' in x and '"decision": "EXECUTED"' in x
def test_duplicate_never_reaches_executor():
    x=body()
    d=x.index('registration.decision == "DUPLICATE"')
    e=x.index("execute_direct_action(")
    assert d<e and 'return' in x[d:e]
def test_endpoint_bypasses_legacy_handle_turn():
    assert "handle_turn" not in body()
