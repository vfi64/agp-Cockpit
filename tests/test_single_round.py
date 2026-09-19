from dataclasses import dataclass

from agp_cockpit.core.single_round import RoundState, SingleDirectExecutionRound


@dataclass
class A:
    action_id:str="a1"
    mode:str="DIRECT_EXECUTION"
    work_order:object=None

def mk(**kw):
    events=[]
    vals={"read_completed": lambda:"FRAME","parse_action": lambda x:A(work_order={"opaque":[1,2]}),
      "dispatch": lambda w:(events.append(("dispatch",w)) or {"rc":0}),
      "make_result": lambda a,r:{"action_id":a.action_id,"local":r},
      "submit_result": lambda r:events.append(("submit",r)),"stopped": lambda:False}
    vals.update(kw)
    return SingleDirectExecutionRound(**vals),events

def test_happy_path_dispatches_opaque_once_submits_once_and_stops():
    r,e=mk(); o=r.run()
    assert o.state is RoundState.DONE
    assert e[0]==("dispatch",{"opaque":[1,2]})
    assert e[1][0]=="submit" and len(e)==2

def test_malformed_blocks_without_dispatch_or_fallback():
    r,e=mk(parse_action=lambda _:(_ for _ in ()).throw(ValueError("bad")))
    assert r.run().state is RoundState.BLOCKED_TRANSPORT and e==[]

def test_file_transfer_dispatches_same_opaque_work_order_and_submits_once():
    r,e=mk(parse_action=lambda _:A(mode="FILE_TRANSFER",work_order={"opaque":[1,2]}))
    o=r.run()
    assert o.state is RoundState.DONE
    assert e[0]==("dispatch",{"opaque":[1,2]})
    assert e[1][0]=="submit" and len(e)==2

def test_unknown_mode_blocks_without_dispatch():
    r,e=mk(parse_action=lambda _:A(mode="UNKNOWN"))
    assert r.run().state is RoundState.BLOCKED_TRANSPORT and e==[]

def test_dispatch_failure_stops_and_never_submits():
    def bad(_): raise RuntimeError("boom")
    r,e=mk(dispatch=bad)
    assert r.run().state is RoundState.FAIL_TRANSPORT and e==[]

def test_stop_before_read_has_no_side_effects():
    called=[]
    r,e=mk(read_completed=lambda:called.append(1),stopped=lambda:True)
    assert r.run().state is RoundState.USER_STOPPED
    assert called==[] and e==[]
