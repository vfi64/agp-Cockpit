from pathlib import Path
import json
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]
P8 = ROOT / "chrome_extension/phase8_multi_round.js"
CC = ROOT / "chrome_extension/conversation_contract.js"

def node(script: str):
    p = subprocess.run(["node", "-e", script], cwd=ROOT, text=True, capture_output=True)
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout.strip()

def p8_harness(sequence, max_rounds=25, extra=""):
    # sequence entries: ACTION, DONE, FAIL, BLOCKED, CANCELLED, TIMEOUT
    js = f"""
global.window=global;
const seq={json.dumps(sequence)};
let waits=0,calls=0,seen=[];
window.AGPCockpitConversationContract={{
  waitForCompletedProtocolAssistant:async o=>{{
    waits++; seen.push(o);
    const x=seq.shift();
    if(x==="TIMEOUT") throw new Error("PHASE8_COMPLETED_PROTOCOL_ASSISTANT_TIMEOUT");
    if(x===undefined) throw new Error("UNEXPECTED_EXTRA_WAIT");
    if(x==="DONE") return {{text:"CONTROL|s|done",fingerprint:"f"+waits}};
    return {{text:"ACTION|"+x,fingerprint:"f"+waits}};
  }}
}};
window.AGPCockpitTransportProtocolV1={{
  parseControl:t=>{{
    if(!t.startsWith("CONTROL|")) throw new Error("not control");
    const p=t.split("|"); return {{control:"DONE",session_id:p[1],round_id:p[2]}};
  }}
}};
window.AGPCockpitPhase7SingleRound={{
  runOneRound:async o=>{{
    calls++;
    const token=o.protocolSnapshot.text.split("|")[1];
    if(["FAIL","BLOCKED","CANCELLED"].includes(token))
      return {{state:"DONE",session_id:"s",assistant_fingerprint:o.protocolSnapshot.fingerprint,transport_status:token}};
    return {{state:"DONE",session_id:"s",round_id:"r"+calls,action_id:"a"+calls,
             assistant_fingerprint:o.protocolSnapshot.fingerprint,transport_status:"PASS"}};
  }}
}};
require({json.dumps(str(P8))});
{extra}
(async()=>{{
  try {{
    const out=await window.AGPCockpitPhase8MultiRound.run({{maxRounds:{max_rounds},pausePollMs:1,browserTimeoutMs:2000}});
    console.log(JSON.stringify({{ok:true,out,calls,waits,seen}}));
  }} catch(e) {{
    console.log(JSON.stringify({{ok:false,error:e.message,calls,waits,seen}}));
  }}
}})();
"""
    return json.loads(node(js))

def test_stress_twenty_actions_then_done_exactly_once_each():
    seq=["PASS"]*20+["DONE"]
    d=p8_harness(seq, max_rounds=25)
    assert d["ok"] is True
    assert d["out"]["state"]=="DONE"
    assert d["out"]["rounds"]==20
    assert d["calls"]==20
    assert d["waits"]==21
    assert d["seen"][0]["afterFingerprint"]==""
    assert [x["afterFingerprint"] for x in d["seen"][1:]] == [f"f{i}" for i in range(1,21)]

def test_done_after_two_actions_has_no_third_dispatch():
    d=p8_harness(["PASS","PASS","DONE"], max_rounds=5)
    assert d["ok"] and d["out"]["state"]=="DONE"
    assert d["calls"]==2 and d["waits"]==3 and d["out"]["rounds"]==2

def test_max_round_boundary_performs_no_extra_wait():
    d=p8_harness(["PASS","PASS","PASS"], max_rounds=3)
    assert d["ok"] and d["out"]["state"]=="MAX_ROUNDS_REACHED"
    assert d["calls"]==3 and d["waits"]==3 and d["out"]["rounds"]==3

def test_terminal_statuses_stop_without_followup_wait():
    for status in ("FAIL","BLOCKED","CANCELLED"):
        d=p8_harness([status], max_rounds=5)
        assert d["ok"] and d["out"]["state"]==status
        assert d["calls"]==1 and d["waits"]==1

def test_initial_timeout_has_zero_dispatch():
    d=p8_harness(["TIMEOUT"], max_rounds=5)
    assert d["ok"] is False
    assert "TIMEOUT" in d["error"]
    assert d["calls"]==0 and d["waits"]==1

def test_timeout_after_first_result_has_one_dispatch_only():
    d=p8_harness(["PASS","TIMEOUT"], max_rounds=5)
    assert d["ok"] is False
    assert "TIMEOUT" in d["error"]
    assert d["calls"]==1 and d["waits"]==2

def test_stop_during_first_execution_prevents_second_wait():
    extra="""
const orig=window.AGPCockpitPhase7SingleRound.runOneRound;
window.AGPCockpitPhase7SingleRound.runOneRound=async o=>{
  const r=await orig(o);
  window.AGPCockpitPhase8MultiRound.stop();
  return r;
};
"""
    d=p8_harness(["PASS"], max_rounds=5, extra=extra)
    assert d["ok"] and d["out"]["state"]=="USER_STOPPED"
    assert d["calls"]==1 and d["waits"]==1 and d["out"]["rounds"]==1

def test_pause_before_dispatch_blocks_execution_until_resume():
    js=f"""
global.window=global;
let calls=0,waits=0;
window.AGPCockpitConversationContract={{
  waitForCompletedProtocolAssistant:async o=>{{waits++;return {{text:"ACTION",fingerprint:"f1"}};}}
}};
window.AGPCockpitTransportProtocolV1={{parseControl:t=>{{throw new Error("not control")}}}};
window.AGPCockpitPhase7SingleRound={{
  runOneRound:async o=>{{calls++;return {{state:"DONE",session_id:"s",assistant_fingerprint:"f1",transport_status:"PASS"}};}}
}};
require({json.dumps(str(P8))});
window.AGPCockpitPhase8MultiRound.pause();
(async()=>{{
  const promise=window.AGPCockpitPhase8MultiRound.run({{maxRounds:1,pausePollMs:2,browserTimeoutMs:2000}});
  await new Promise(r=>setTimeout(r,20));
  if(calls!==0) throw new Error("DISPATCHED_WHILE_PAUSED");
  window.AGPCockpitPhase8MultiRound.resume();
  const out=await promise;
  console.log(JSON.stringify({{calls,waits,state:out.state,rounds:out.rounds}}));
}})().catch(e=>{{console.error(e);process.exit(1);}});
"""
    d=json.loads(node(js))
    assert d=={"calls":1,"waits":1,"state":"MAX_ROUNDS_REACHED","rounds":1}

def test_real_protocol_waiter_survives_streaming_then_requires_stability():
    frame='AGP_COCKPIT_ACTION_BEGIN\\n{"protocol_version":1}\\nAGP_COCKPIT_ACTION_END'
    js=f"""
global.window=global;
global.crypto=require("crypto").webcrypto;
global.location={{href:"https://chatgpt.com/c/test"}};
global.chrome={{storage:{{local:{{get:async()=>({{conversationUrl:"https://chatgpt.com/c/test"}})}}}}}};
global.HTMLTextAreaElement=function(){{}};
let streamingChecks=2;
const pre={{textContent:{json.dumps(frame)}}};
const assistant={{
  innerText:{json.dumps(frame)},
  textContent:{json.dumps(frame)},
  getBoundingClientRect:()=>({{width:10,height:10}}),
  querySelectorAll:s=>s==="pre"?[pre]:[]
}};
global.document={{
  querySelector:s=>{{
    if(s==='button[data-testid="stop-button"]' && streamingChecks>0){{streamingChecks--;return {{disabled:false}};}}
    return null;
  }},
  querySelectorAll:s=>s==='[data-message-author-role="assistant"]'?[assistant]:[]
}};
require({json.dumps(str(CC))});
(async()=>{{
  const out=await global.AGPCockpitConversationContract.waitForCompletedProtocolAssistant({{
    afterFingerprint:"",timeoutMs:1000,pollMs:1,stablePolls:3
  }});
  console.log(JSON.stringify({{source:out.source,stablePolls:out.stablePolls,text:out.text,streamingChecks}}));
}})().catch(e=>{{console.error(e);process.exit(1);}});
"""
    d=json.loads(node(js))
    assert d["source"]=="pre"
    assert d["stablePolls"]>=3
    assert d["streamingChecks"]==0
    assert d["text"].startswith("AGP_COCKPIT_ACTION_BEGIN")

def test_real_protocol_waiter_same_fingerprint_times_out_instead_of_replaying():
    frame='AGP_COCKPIT_ACTION_BEGIN\\n{"protocol_version":1}\\nAGP_COCKPIT_ACTION_END'
    js=f"""
global.window=global;
global.crypto=require("crypto").webcrypto;
global.location={{href:"https://chatgpt.com/c/test"}};
global.chrome={{storage:{{local:{{get:async()=>({{conversationUrl:"https://chatgpt.com/c/test"}})}}}}}};
global.HTMLTextAreaElement=function(){{}};
const pre={{textContent:{json.dumps(frame)}}};
const assistant={{
  innerText:{json.dumps(frame)},textContent:{json.dumps(frame)},
  getBoundingClientRect:()=>({{width:10,height:10}}),
  querySelectorAll:s=>s==="pre"?[pre]:[]
}};
global.document={{
  querySelector:s=>null,
  querySelectorAll:s=>s==='[data-message-author-role="assistant"]'?[assistant]:[]
}};
require({json.dumps(str(CC))});
(async()=>{{
  const C=global.AGPCockpitConversationContract;
  const first=await C.waitForCompletedProtocolAssistant({{afterFingerprint:"",timeoutMs:500,pollMs:1,stablePolls:2}});
  let msg="";
  try{{await C.waitForCompletedProtocolAssistant({{afterFingerprint:first.fingerprint,timeoutMs:25,pollMs:1,stablePolls:2}});}}
  catch(e){{msg=e.message;}}
  console.log(JSON.stringify({{msg}}));
}})().catch(e=>{{console.error(e);process.exit(1);}});
"""
    d=json.loads(node(js))
    assert d["msg"]=="PHASE8_COMPLETED_PROTOCOL_ASSISTANT_TIMEOUT"
