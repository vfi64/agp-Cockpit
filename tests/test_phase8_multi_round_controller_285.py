from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/"chrome_extension/phase8_multi_round.js"

def case(tmp_path, body):
    h=tmp_path/"h.js"
    pre=(
        "global.window=global;let calls=0,waits=0;"
        "window.AGPCockpitPhase7SingleRound={runOneRound:async o=>{calls++;return global.nextResult(calls,o);}};"
        "window.AGPCockpitConversationContract={waitForCompletedProtocolAssistant:async o=>{waits++;return {text:'ACTION',fingerprint:'f'+waits}}};"
        "window.AGPCockpitTransportProtocolV1={parseControl:t=>{throw Error('not control')}};"
    )
    h.write_text(pre+"require("+json.dumps(str(JS))+");(async()=>{"+body+"})().catch(e=>{console.error(e);process.exit(9)});")
    return subprocess.run(["node",str(h)],capture_output=True,text=True)

def test_bounded_rounds(tmp_path):
    p=case(tmp_path,'global.nextResult=n=>({state:"DONE",session_id:"s",assistant_fingerprint:"f"+n,transport_status:"PASS"});let o=await window.AGPCockpitPhase8MultiRound.run({maxRounds:3,pausePollMs:1});if(o.state!=="MAX_ROUNDS_REACHED"||o.rounds!==3||calls!==3||waits!==3)process.exit(2);')
    assert p.returncode==0,p.stderr

def test_fail_block_cancel_terminate(tmp_path):
    for s in ("FAIL","BLOCKED","CANCELLED"):
        p=case(tmp_path,f'global.nextResult=n=>({{state:"DONE",session_id:"s",assistant_fingerprint:"f"+n,transport_status:"{s}"}});let o=await window.AGPCockpitPhase8MultiRound.run({{maxRounds:5,pausePollMs:1}});if(o.state!=="{s}"||calls!==1||waits!==1)process.exit(2);')
        assert p.returncode==0,p.stderr

def test_stop_between_rounds(tmp_path):
    p=case(tmp_path,'global.nextResult=n=>{if(n===1)window.AGPCockpitPhase8MultiRound.stop();return {state:"DONE",session_id:"s",assistant_fingerprint:"f"+n,transport_status:"PASS"}};let o=await window.AGPCockpitPhase8MultiRound.run({maxRounds:5,pausePollMs:1});if(o.state!=="USER_STOPPED"||o.rounds!==1||calls!==1||waits!==1)process.exit(2);')
    assert p.returncode==0,p.stderr

def test_invalid_limit_no_dispatch(tmp_path):
    p=case(tmp_path,'global.nextResult=()=>({state:"DONE",transport_status:"PASS"});let ok=false;try{await window.AGPCockpitPhase8MultiRound.run({maxRounds:0})}catch(e){ok=e.message==="PHASE8_INVALID_MAX_ROUNDS"}if(!ok||calls!==0||waits!==0)process.exit(2);')
    assert p.returncode==0,p.stderr

def test_reuses_phase7_without_transport_duplication():
    t=JS.read_text()
    assert "AGPCockpitPhase7SingleRound" in t
    assert "/v1/protocol/execute" not in t
    assert "fetch(" not in t
