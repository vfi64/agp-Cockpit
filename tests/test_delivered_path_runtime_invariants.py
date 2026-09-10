from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_f01_delivered_http_path_uses_durable_task_controller_before_execution():
    source=(ROOT/'src/agp_cockpit/core/bridge_server.py').read_text(encoding='utf-8')
    start=source.index('if path == "/v1/protocol/execute":')
    body=source[start:source.index('if path == "/v1/turn":',start)]
    assert 'durable_controller_for(action.session_id)' in body
    assert body.index('durable.accept_remote_action(') < body.index('execute_direct_action(')
    assert 'durable_decision == "DUPLICATE"' in body

def test_f02_delivered_runtime_uses_stable_persistent_duplicate_store():
    runtime=(ROOT/'src/agp_cockpit/core/bridge_runtime_server.py').read_text(encoding='utf-8')
    server=(ROOT/'src/agp_cockpit/core/bridge_server.py').read_text(encoding='utf-8')
    assert 'runtime_root=self.local_root' in runtime
    assert 'self._durable_db_path = self.runtime_root / "protocol-v1-actions.sqlite3"' in server
    assert 'DurableTaskController(' in server

def test_f03_delivered_execute_path_retains_real_execution_policy_boundary():
    server=(ROOT/'src/agp_cockpit/core/bridge_server.py').read_text(encoding='utf-8')
    execution=(ROOT/'src/agp_cockpit/core/bridge_execution.py').read_text(encoding='utf-8')
    assert 'execute_direct_action(' in server
    assert '_validate_root(order' in execution
    assert 'ExecutionPolicy' in execution
