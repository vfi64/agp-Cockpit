from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1]
STORE=(ROOT/"src/agp_cockpit/core/start_request.py").read_text()
CLIENT=(ROOT/"src/agp_cockpit/core/start_request_client.py").read_text()
SIMPLE=(ROOT/"src/agp_cockpit/ui/simple_task_panel.py").read_text()
BRIDGE=(ROOT/"src/agp_cockpit/core/bridge_server.py").read_text()

def test_start_request_store_carries_task_identity():
    assert "task_id:str=''" in STORE
    assert "'task_id':str(task_id)" in STORE

def test_client_sends_task_identity():
    assert "task_id:str=''" in CLIENT
    assert "'task_id':task_id" in CLIENT

def test_simple_surface_prepares_and_propagates_task_identity():
    assert "self.api.prepare_task_contract(self.contract)" in SIMPLE
    assert 'task_id=str(self.contract.get("task_id") or "")' in SIMPLE

def test_bridge_persists_start_request_task_id():
    block=BRIDGE.split('if path == "/v1/task/start-request":',2)[-1]
    assert 'task_id=str(data.get("task_id","")).strip()' in block
    assert "task_id=task_id" in block
