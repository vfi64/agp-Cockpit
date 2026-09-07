from pathlib import Path
import subprocess, textwrap
ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"chrome_extension/phase7_single_round.js").read_text()
def test_controller_uses_execute_not_validation_or_legacy():
    assert '"/v1/protocol/execute"' in JS
    assert '"/v1/protocol/action"' not in JS
    assert '"/v1/turn"' not in JS
def test_result_is_validated_correlated_and_sent_via_safe_contract():
    for x in ["P.parseResult(data.result_frame)","result.action_id !== action.action_id","C.stageDraft(data.result_frame)","C.approveCurrentDraft()","C.sendApprovedDraft(approval)"]:
        assert x in JS
def test_completed_duplicate_replays_result_without_redispatch():
    decision=JS.index('["EXECUTED","REPLAYED"].includes(data.decision)')
    stage=JS.index("C.stageDraft")
    assert decision < stage
    assert 'data.decision === "DUPLICATE"' not in JS
    assert "DUPLICATE_STOP" not in JS
def test_fake_browser_one_round_stops(tmp_path):
    harness=tmp_path/"h.js"
    harness.write_text('''
global.window=global;
let sent=0, staged=0, fetched=0;
global.chrome={storage:{local:{get:async()=>({baseUrl:"http://127.0.0.1:8765",token:"t"})}}};
window.AGPCockpitConversationContract={
 waitForCompletedProtocolAssistant:async()=>({text:"FRAME",fingerprint:"f",source:"pre"}),
 stageDraft:async x=>{staged++; if(x!=="RESULT") throw Error("bad frame")},
 approveCurrentDraft:async()=>({ok:true}),
 sendApprovedDraft:async()=>{sent++}
};
window.AGPCockpitTransportProtocolV1={
 parseAction:()=>({mode:"DIRECT_EXECUTION",action_id:"a",session_id:"s",round_id:"r"}),
 parseResult:()=>({action_id:"a",session_id:"s",round_id:"r",transport_status:"PASS"})
};
global.fetch=async()=>{fetched++; return {ok:true,json:async()=>({decision:"EXECUTED",result_frame:"RESULT"})}};
require(process.argv[2]);
window.AGPCockpitPhase7SingleRound.runOneRound().then(o=>{
 if(o.state!=="DONE"||fetched!==1||staged!==1||sent!==1) process.exit(2);
 console.log("FAKE_BROWSER_SINGLE_ROUND_PASS");
}).catch(e=>{console.error(e);process.exit(3)});
''')
    p=subprocess.run(["node",str(harness),str(ROOT/"chrome_extension/phase7_single_round.js")],capture_output=True,text=True)
    assert p.returncode==0, p.stdout+p.stderr
    assert "FAKE_BROWSER_SINGLE_ROUND_PASS" in p.stdout


def test_phase7_snapshot_contract_extracts_single_protocol_frame_from_assistant_chrome():
    text = Path("chrome_extension/conversation_contract.js").read_text()
    assert "AGP_PHASE7_PROTOCOL_TEXT_EXTRACTION_259" in text
    assert "extractSingleProtocolFrame(observedText)" in text
    assert "PHASE7_PROTOCOL_FRAME_AMBIGUOUS" in text
    assert '["AGP_COCKPIT_ACTION_BEGIN", "AGP_COCKPIT_ACTION_END"]' in text

def test_phase7_uses_verbatim_protocol_block_snapshot_260():
    contract = Path("chrome_extension/conversation_contract.js").read_text()
    controller = Path("chrome_extension/phase7_single_round.js").read_text()
    assert "AGP_PHASE7_VERBATIM_PROTOCOL_BLOCK_260" in contract
    assert 'assistant.querySelectorAll("pre")' in contract
    assert "PHASE7_PROTOCOL_BLOCK_COUNT" in contract
    assert "PHASE7_PROTOCOL_BLOCK_NOT_PURE_FRAME" in contract
    assert 'source = "pre"' in contract
    assert "currentAssistantProtocolSnapshot," in contract
    assert "C.waitForCompletedProtocolAssistant(" in controller
    assert "C.currentAssistantSnapshot()" not in controller
