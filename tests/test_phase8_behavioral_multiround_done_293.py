from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/"chrome_extension/phase8_multi_round.js"

def run_case(tmp_path, body):
    h=tmp_path/"phase8.js"
    pre=(
        "global.window=global;let calls=0,waits=0;"
        "window.AGPCockpitPhase7SingleRound={runOneRound:async o=>{calls++;return global.round(calls,o);}};"
        "window.AGPCockpitConversationContract={waitForCompletedProtocolAssistant:async o=>{waits++;return global.answer(waits,o);}};"
        "window.AGPCockpitTransportProtocolV1={parseControl:t=>{if(!t.startsWith('CONTROL|'))throw Error('not control');let p=t.split('|');return {control:'DONE',session_id:p[1],round_id:p[2]}}};"
    )
    h.write_text(pre+"require("+json.dumps(str(JS))+");(async()=>{"+body+"})().catch(e=>{console.error(e);process.exit(9)});")
    return subprocess.run(["node",str(h)],capture_output=True,text=True)

def test_two_pass_rounds_then_browser_done_without_third_dispatch(tmp_path):
    p=run_case(tmp_path,"global.round=n=>({state:'DONE',session_id:'s',round_id:'r'+n,action_id:'a'+n,assistant_fingerprint:'f'+n,transport_status:'PASS'});global.answer=n=>({text:n<3?'ACTION':'CONTROL|s|done',fingerprint:'f'+n});let o=await window.AGPCockpitPhase8MultiRound.run({maxRounds:3,pausePollMs:1});if(o.state!=='DONE'||o.rounds!==2||calls!==2||waits!==3)process.exit(2);")
    assert p.returncode==0,p.stderr

def test_done_session_mismatch_fails_closed(tmp_path):
    p=run_case(tmp_path,"global.round=n=>({state:'DONE',session_id:'s',assistant_fingerprint:'f'+n,transport_status:'PASS'});global.answer=n=>({text:n===1?'ACTION':'CONTROL|other|done',fingerprint:'f'+n});let ok=false;try{await window.AGPCockpitPhase8MultiRound.run({maxRounds:3,pausePollMs:1})}catch(e){ok=e.message==='PHASE8_DONE_SESSION_MISMATCH'}if(!ok||calls!==1||waits!==2)process.exit(2);")
    assert p.returncode==0,p.stderr

def test_fail_stops_before_further_wait_or_redispatch(tmp_path):
    p=run_case(tmp_path,"global.round=n=>({state:'DONE',session_id:'s',assistant_fingerprint:'f'+n,transport_status:'FAIL'});global.answer=n=>({text:'ACTION',fingerprint:'f'+n});let o=await window.AGPCockpitPhase8MultiRound.run({maxRounds:3,pausePollMs:1});if(o.state!=='FAIL'||calls!==1||waits!==1)process.exit(2);")
    assert p.returncode==0,p.stderr
