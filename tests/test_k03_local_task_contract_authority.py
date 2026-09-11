from pathlib import Path
import pytest
from agp_cockpit.core.task_contract import LocalTaskContract
from agp_cockpit.core.task_controller import DurableTaskController

def test_deny_default(tmp_path):
    c=LocalTaskContract(tmp_path)
    assert not c.allows(effect="E0",tool="read")

def test_bad_effect(tmp_path):
    with pytest.raises(ValueError):
        LocalTaskContract(tmp_path,allowed_effects=frozenset({"E9"}))

def test_persisted_local_authority(tmp_path):
    root=tmp_path/"repo"; root.mkdir()
    contract=LocalTaskContract(root,frozenset({"E0","E2"}),frozenset({"read","python"}))
    c=DurableTaskController("task",tmp_path/"db.sqlite3",local_contract=contract)
    import json
    stored=c.store.task_authority("task")
    assert stored is not None
    assert Path(stored["repository_root"]) == root.resolve()
    assert set(json.loads(stored["allowed_effects_json"])) == {"E0","E2"}
    assert set(json.loads(stored["allowed_tools_json"])) == {"read","python"}
    assert c.action_authorized({"effect":"E2","argv":["python"],"cwd":str(root)})
    assert not c.action_authorized({"effect":"E3","argv":["agentic-kit"],"cwd":str(root)})
    c.close()

def test_remote_payload_cannot_expand(tmp_path):
    root=tmp_path/"repo"; root.mkdir()
    c=DurableTaskController("task",tmp_path/"db.sqlite3",local_contract=LocalTaskContract(root))
    import json
    payload={"effect":"E4","argv":["network"],"cwd":str(root),"allowed_effects":["E4"],"allowed_tools":["network"]}
    assert c.accept_remote_action("a1",payload)=="NEW"
    assert not c.action_authorized(payload)
    stored=c.store.task_authority("task")
    assert json.loads(stored["allowed_effects_json"]) == []
    assert json.loads(stored["allowed_tools_json"]) == []
    c.close()

def test_network_authority_is_local_and_persisted(tmp_path):
    root=tmp_path/'repo'; root.mkdir()
    denied=LocalTaskContract(root,frozenset({'E4'}),frozenset({'curl'}),allow_network=False)
    c=DurableTaskController('network-denied',tmp_path/'network.sqlite3',local_contract=denied)
    assert not c.action_authorized({'effect':'E4','argv':['curl'],'cwd':str(root)})
    assert not bool(c.store.task_authority(c.task_id)['allow_network']); c.close()
    allowed=LocalTaskContract(root,frozenset({'E4'}),frozenset({'curl'}),allow_network=True)
    c=DurableTaskController('network-allowed',tmp_path/'network.sqlite3',local_contract=allowed)
    assert c.action_authorized({'effect':'E4','argv':['curl'],'cwd':str(root)})
    assert bool(c.store.task_authority(c.task_id)['allow_network']); c.close()
