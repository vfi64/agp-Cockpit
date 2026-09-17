from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
API=(ROOT/"src/agp_cockpit/core/task_operator_api.py").read_text()
BRIDGE=(ROOT/"src/agp_cockpit/core/bridge_server.py").read_text()

def test_task_start_persists_existing_local_authority_under_real_task_id():
    body=API.split("def start_task_from_contract",1)[1]
    assert "self.local_contract" in body
    assert "settings_path" not in body
    assert "self.controller.set_task_authority(" in body
    assert "allowed_effects=self.local_contract.allowed_effects" in body
    assert "allowed_tools=self.local_contract.allowed_tools" in body

def test_protocol_session_is_not_unconditionally_used_as_task_identity():
    body=BRIDGE.split("def _durable_controller",1)[1].split("def start",1)[0]
    assert "StartRequestStore" in body
    assert 'current.get("task_id")' in body
