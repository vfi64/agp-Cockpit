import json

from agp_cockpit.core.task_contract import LocalTaskContract
from agp_cockpit.core.task_operator_api import TaskOperatorAPI


def test_injected_authority_is_persisted_under_real_task_id(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME",str(tmp_path/"home"))
    repo=tmp_path/"repo"; repo.mkdir()
    contract=LocalTaskContract(repo,allowed_effects=frozenset({"E2"}),allowed_tools=frozenset({"git"}),allow_network=False)
    api=TaskOperatorAPI(repo,local_contract=contract)
    api.start_task_from_contract({"task_id":"authority-1339","goal":"test"})
    a=api.controller.store.task_authority("authority-1339")
    assert a is not None
    assert set(json.loads(a["allowed_effects_json"]))=={"E2"}
    assert set(json.loads(a["allowed_tools_json"]))=={"git"}
    assert not bool(a["allow_network"])

def test_missing_injected_contract_remains_fail_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME",str(tmp_path/"home"))
    repo=tmp_path/"repo"; repo.mkdir()
    api=TaskOperatorAPI(repo)
    api.start_task_from_contract({"task_id":"closed-1339","goal":"test"})
    a=api.controller.store.task_authority("closed-1339")
    assert a is not None
    assert json.loads(a["allowed_effects_json"])==[]
    assert json.loads(a["allowed_tools_json"])==[]
    assert not bool(a["allow_network"])
