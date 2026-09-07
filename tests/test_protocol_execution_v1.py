from types import SimpleNamespace
import pytest
import agp_cockpit.core.protocol_execution_v1 as m
from agp_cockpit.core.transport_protocol_v1 import ActionEnvelope, parse_result_frame

def action(content='{"kind":"noop"}'):
    return ActionEnvelope(1,"s","r","a","DIRECT_EXECUTION",{"repository_path_hint":"/repo"},{"type":"terminal_payload","content":content})

def test_exact_opaque_content_is_forwarded_and_result_is_canonical(monkeypatch,tmp_path):
    seen={}
    def fake(text,**kw):
        seen["text"]=text
        return SimpleNamespace(returncode=0,timed_out=False,result_block="bounded")
    monkeypatch.setattr(m,"execute_structured_work_order",fake)
    raw=' { "kind" : "noop" } '
    frame=m.execute_direct_action(action(raw),repository_root=tmp_path,kit_binary=tmp_path/"kit")
    assert seen["text"]==raw
    r=parse_result_frame(frame)
    assert r.transport_status=="PASS"
    assert r.local_execution=={"return_code":0,"bounded_output":"bounded","log_ref":None}

def test_nonzero_maps_transport_execution_failure_without_interpreting_output(monkeypatch,tmp_path):
    monkeypatch.setattr(m,"execute_structured_work_order",lambda *a,**k:SimpleNamespace(returncode=7,timed_out=False,result_block="KIT PASS text is opaque"))
    r=parse_result_frame(m.execute_direct_action(action(),repository_root=tmp_path,kit_binary=tmp_path/"kit"))
    assert r.transport_status=="FAIL"
    assert r.local_execution["bounded_output"]=="KIT PASS text is opaque"

def test_file_transfer_forwards_exact_opaque_content_through_same_local_executor(monkeypatch,tmp_path):
    seen={}
    def fake(text,**kw):
        seen["text"]=text
        seen["repository_root"]=kw["repository_root"]
        seen["kit_binary"]=kw["kit_binary"]
        return SimpleNamespace(returncode=0,timed_out=False,result_block="kit-file-transfer-output")
    monkeypatch.setattr(m,"execute_structured_work_order",fake)
    a=action(' { "kind" : "kit-file-transfer" } ')
    a=ActionEnvelope(a.protocol_version,a.session_id,a.round_id,a.action_id,"FILE_TRANSFER",a.target,a.work_order)
    kit=tmp_path/"kit"
    r=parse_result_frame(m.execute_direct_action(a,repository_root=tmp_path,kit_binary=kit))
    assert seen["text"]==' { "kind" : "kit-file-transfer" } '
    assert seen["repository_root"]==tmp_path
    assert seen["kit_binary"]==kit
    assert r.transport_status=="PASS"
    assert r.local_execution=={"return_code":0,"bounded_output":"kit-file-transfer-output","log_ref":None}

def test_rejects_unknown_execution_mode(tmp_path):
    a=action()
    a=ActionEnvelope(a.protocol_version,a.session_id,a.round_id,a.action_id,"UNKNOWN",a.target,a.work_order)
    with pytest.raises(ValueError):
        m.execute_direct_action(a,repository_root=tmp_path,kit_binary=tmp_path/"kit")
