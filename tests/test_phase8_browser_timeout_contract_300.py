from pathlib import Path
import json, subprocess
ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/"chrome_extension/phase8_multi_round.js"

def run_case(tmp_path, body):
    h=tmp_path/"phase8_timeout.js"
    pre=(
        "global.window=global;let seen=[];"
        "window.AGPCockpitPhase7SingleRound={runOneRound:async o=>({state:'DONE',session_id:'s',assistant_fingerprint:o.protocolSnapshot.fingerprint,transport_status:'PASS'})};"
        "window.AGPCockpitConversationContract={waitForCompletedProtocolAssistant:async o=>{seen.push(o);return seen.length===1?{text:'ACTION',fingerprint:'f1'}:{text:'CONTROL|s|done',fingerprint:'f2'}}};"
        "window.AGPCockpitTransportProtocolV1={parseControl:t=>{if(t.startsWith('CONTROL|'))return {control:'DONE',session_id:'s',round_id:'done'};throw Error('not control')}};"
    )
    h.write_text(pre+"require("+json.dumps(str(JS))+");(async()=>{"+body+"})().catch(e=>{console.error(e);process.exit(9)});")
    return subprocess.run(["node",str(h)],capture_output=True,text=True)

def test_default_browser_wait_timeout_is_120_seconds(tmp_path):
    p=run_case(tmp_path,"let o=await window.AGPCockpitPhase8MultiRound.run({maxRounds:2,pausePollMs:1});if(o.state!=='DONE'||seen.length!==2||seen.some(x=>x.timeoutMs!==120000))process.exit(2);")
    assert p.returncode==0,p.stderr

def test_browser_wait_timeout_can_be_overridden(tmp_path):
    p=run_case(tmp_path,"await window.AGPCockpitPhase8MultiRound.run({maxRounds:2,pausePollMs:1,browserTimeoutMs:45000});if(seen.length!==2||seen.some(x=>x.timeoutMs!==45000))process.exit(2);")
    assert p.returncode==0,p.stderr

def test_invalid_browser_timeout_fails_before_dispatch(tmp_path):
    p=run_case(tmp_path,"let ok=false;try{await window.AGPCockpitPhase8MultiRound.run({browserTimeoutMs:999})}catch(e){ok=e.message==='PHASE8_INVALID_BROWSER_TIMEOUT'}if(!ok||seen.length!==0)process.exit(2);")
    assert p.returncode==0,p.stderr

def test_source_has_explicit_timeout_marker():
    t=JS.read_text()
    assert "AGP_PHASE8_BROWSER_WAIT_TIMEOUT_300" in t
    assert "browserTimeoutMs=120000" in t
    assert "timeoutMs:browserTimeoutMs" in t
