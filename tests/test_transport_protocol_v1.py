import json
import pytest
from agp_cockpit.core.transport_protocol_v1 import *
def action(**kw):
    d=dict(protocol_version=1,session_id="s1",round_id="r1",action_id="a1",mode="DIRECT_EXECUTION",target={"repository_path_hint":"/repo"},work_order={"opaque":["x",1]}); d.update(kw); return ActionEnvelope(**d)
def test_action_roundtrip_preserves_opaque_work_order():
    a=action(work_order={"anything":{"nested":[1,True,None]}}); assert parse_action_frame(encode_action_frame(a))==a
def test_result_roundtrip():
    r=ResultEnvelope(1,"s1","r1","a1","PASS",{"opaque":"result"}); assert parse_result_frame(encode_result_frame(r))==r
@pytest.mark.parametrize("bad",['{"protocol_version":1}',ACTION_BEGIN+'{"protocol_version":1}'+ACTION_END,ACTION_BEGIN+'\n{}\n',ACTION_BEGIN+'\n{}\n'+ACTION_END+'\nprose',ACTION_BEGIN+'\n'+ACTION_BEGIN+'\n{}\n'+ACTION_END])
def test_malformed_frames_fail_closed(bad):
    with pytest.raises(ProtocolViolation): parse_action_frame(bad)
def test_multiple_frames_rejected():
    f=encode_action_frame(action())
    with pytest.raises(ProtocolViolation): parse_action_frame(f+"\n"+f)
def test_unsupported_version_rejected():
    raw=encode_action_frame(action()).replace('"protocol_version":1','"protocol_version":2')
    with pytest.raises(ProtocolViolation,match="unsupported"): parse_action_frame(raw)
def test_unknown_fields_rejected():
    data=json.loads(encode_action_frame(action()).splitlines()[1]); data["surprise"]=1
    with pytest.raises(ProtocolViolation,match="invalid fields"): parse_action_frame(ACTION_BEGIN+"\n"+json.dumps(data)+"\n"+ACTION_END)
@pytest.mark.parametrize("mode",["DIRECT_EXECUTION","FILE_TRANSFER"])
def test_both_protocol_modes(mode): assert parse_action_frame(encode_action_frame(action(mode=mode))).mode==mode
def test_invalid_mode_rejected():
    with pytest.raises(ProtocolViolation): encode_action_frame(action(mode="OTHER"))
def test_duplicate_same_action_is_not_redispatched():
    reg=ActionRegistry(); a=action(); assert reg.register(a).decision=="DISPATCH"; assert reg.register(a).decision=="DUPLICATE"
def test_changed_payload_under_same_action_id_is_violation():
    reg=ActionRegistry(); reg.register(action())
    with pytest.raises(ProtocolViolation,match="changed payload"): reg.register(action(work_order={"different":True}))
def test_ambiguous_execution_is_never_auto_replayed():
    reg=ActionRegistry(); a=action(); reg.register(a); reg.mark_ambiguous("a1")
    with pytest.raises(ProtocolViolation,match="automatic replay forbidden"): reg.register(a)
def test_target_is_required_transport_metadata():
    with pytest.raises(ProtocolViolation): encode_action_frame(action(target=""))
def test_oversized_frame_rejected():
    with pytest.raises(ProtocolViolation,match="maximum size"): parse_action_frame(ACTION_BEGIN+"\n"+("x"*2_000_001)+"\n"+ACTION_END)
@pytest.mark.parametrize("status",["PASS","BLOCKED","FAIL","DONE","CANCELLED"])
def test_all_result_statuses(status):
    r=ResultEnvelope(1,"s","r","a",status,{"x":1}); assert parse_result_frame(encode_result_frame(r)).transport_status==status
