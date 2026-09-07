from pathlib import Path
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
P8=(ROOT/"chrome_extension/phase8_multi_round.js").read_text()
UI=(ROOT/"chrome_extension/content.js").read_text()

def node(script):
    p=subprocess.run(["node","-e",script],cwd=ROOT,text=True,capture_output=True)
    assert p.returncode==0,p.stdout+p.stderr
    return p.stdout.strip()

def test_controller_exposes_optional_round_completion_callback():
    assert "onRoundCompleted=null" in P8
    assert "AGP_PHASE8_LIVE_ROUND_PROGRESS_328" in P8
    assert "onRoundCompleted(Object.freeze({rounds:completed,last}))" in P8

def test_ui_updates_turns_during_run_not_only_at_end():
    assert "AGP_PHASE8_UI_LIVE_ROUND_PROGRESS_328" in UI
    assert "onRoundCompleted: ({rounds}) => {" in UI
    assert "STATE.turns = Number(rounds || 0);" in UI
    assert 'STATE.lastEvent = "PHASE8_ROUND_COMPLETED";' in UI

def test_two_rounds_emit_progress_one_then_two():
    js=f"""
global.window=global;
const seq=[
 {{text:"ACTION1",fingerprint:"f1"}},
 {{text:"ACTION2",fingerprint:"f2"}},
 {{text:"CONTROL|s|done",fingerprint:"f3"}}
];
let calls=0,progress=[];
window.AGPCockpitConversationContract={{
 waitForCompletedProtocolAssistant:async()=>seq.shift()
}};
window.AGPCockpitTransportProtocolV1={{
 parseControl:t=>{{if(t.startsWith("CONTROL|"))return {{control:"DONE",session_id:"s",round_id:"done"}};throw Error("not control");}}
}};
window.AGPCockpitPhase7SingleRound={{
 runOneRound:async o=>{{calls++;return {{state:"DONE",session_id:"s",assistant_fingerprint:o.protocolSnapshot.fingerprint,transport_status:"PASS"}};}}
}};
eval({json.dumps(P8)});
(async()=>{{
 const out=await window.AGPCockpitPhase8MultiRound.run({{
   maxRounds:5,pausePollMs:1,browserTimeoutMs:2000,
   onRoundCompleted:e=>progress.push(e.rounds)
 }});
 console.log(JSON.stringify({{state:out.state,rounds:out.rounds,calls,progress}}));
}})().catch(e=>{{console.error(e);process.exit(1);}});
"""
    d=json.loads(node(js))
    assert d=={"state":"DONE","rounds":2,"calls":2,"progress":[1,2]}

def test_callback_failure_cannot_break_transport_state_machine():
    js=f"""
global.window=global;
const seq=[
 {{text:"ACTION1",fingerprint:"f1"}},
 {{text:"CONTROL|s|done",fingerprint:"f2"}}
];
let calls=0;
window.AGPCockpitConversationContract={{waitForCompletedProtocolAssistant:async()=>seq.shift()}};
window.AGPCockpitTransportProtocolV1={{
 parseControl:t=>{{if(t.startsWith("CONTROL|"))return {{control:"DONE",session_id:"s",round_id:"done"}};throw Error("not control");}}
}};
window.AGPCockpitPhase7SingleRound={{
 runOneRound:async o=>{{calls++;return {{state:"DONE",session_id:"s",assistant_fingerprint:o.protocolSnapshot.fingerprint,transport_status:"PASS"}};}}
}};
eval({json.dumps(P8)});
(async()=>{{
 const out=await window.AGPCockpitPhase8MultiRound.run({{
   maxRounds:5,pausePollMs:1,browserTimeoutMs:2000,
   onRoundCompleted:()=>{{throw Error("ui callback failure")}}
 }});
 console.log(JSON.stringify({{state:out.state,rounds:out.rounds,calls}}));
}})().catch(e=>{{console.error(e);process.exit(1);}});
"""
    d=json.loads(node(js))
    assert d=={"state":"DONE","rounds":1,"calls":1}

def test_initial_timeout_emits_no_progress():
    js=f"""
global.window=global;
let progress=0,calls=0;
window.AGPCockpitConversationContract={{
 waitForCompletedProtocolAssistant:async()=>{{throw Error("PHASE8_COMPLETED_PROTOCOL_ASSISTANT_TIMEOUT");}}
}};
window.AGPCockpitTransportProtocolV1={{parseControl:()=>{{throw Error("x")}}}};
window.AGPCockpitPhase7SingleRound={{runOneRound:async()=>{{calls++;}}}};
eval({json.dumps(P8)});
(async()=>{{
 let msg="";
 try{{await window.AGPCockpitPhase8MultiRound.run({{maxRounds:5,onRoundCompleted:()=>progress++}});}}
 catch(e){{msg=e.message;}}
 console.log(JSON.stringify({{msg,progress,calls}}));
}})();
"""
    d=json.loads(node(js))
    assert "TIMEOUT" in d["msg"]
    assert d["progress"]==0 and d["calls"]==0
