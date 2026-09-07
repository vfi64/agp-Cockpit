from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "chrome_extension/phase7_single_round.js"

def _run(tmp_path, mode):
    h = tmp_path / f"phase9_{mode}.js"
    h.write_text(r'''
global.window = global;
let sent = 0;
let fetched = 0;
global.chrome = {storage:{local:{get:async()=>({token:"t", baseUrl:"http://127.0.0.1:8765"})}}};
window.AGPCockpitConversationContract = {
  currentAssistantSnapshot: async()=>({text:"FRAME", fingerprint:"fp"}),
  waitForCompletedProtocolAssistant: async()=>({text:"FRAME", fingerprint:"fp"}),
  stageDraft: async x=>{ if(x!=="RESULT") throw Error("bad result"); },
  approveCurrentDraft: async()=>({ok:true}),
  sendApprovedDraft: async()=>{ sent++; }
};
window.AGPCockpitTransportProtocolV1 = {
  parseAction: ()=>({mode:process.argv[3], action_id:"a", session_id:"s", round_id:"r"}),
  parseResult: ()=>({action_id:"a", session_id:"s", round_id:"r", transport_status:"FAIL"})
};
global.fetch = async()=>{
  fetched++;
  return {ok:true, json:async()=>({decision:"EXECUTED", result_frame:"RESULT"})};
};
require(process.argv[2]);
window.AGPCockpitPhase7SingleRound.runOneRound().then(o=>{
  if(o.state!=="DONE" || fetched!==1 || sent!==1) process.exit(2);
  console.log("MODE_OK="+process.argv[3]+" STATUS="+o.transport_status);
}).catch(e=>{ console.error(e); process.exit(3); });
''')
    return subprocess.run(["node", str(h), str(JS), mode], capture_output=True, text=True)

def test_source_accepts_direct_and_file_transfer_through_same_execute_path():
    t = JS.read_text()
    assert '["DIRECT_EXECUTION", "FILE_TRANSFER"].includes(action.mode)' in t
    assert '"/v1/protocol/execute"' in t
    assert "P.parseResult(data.result_frame)" in t
    assert "C.stageDraft(data.result_frame)" in t
    assert "C.sendApprovedDraft(approval)" in t

def test_direct_execution_still_uses_same_path(tmp_path):
    p = _run(tmp_path, "DIRECT_EXECUTION")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "MODE_OK=DIRECT_EXECUTION" in p.stdout

def test_file_transfer_uses_same_path_and_can_return_kit_fail_closed_result(tmp_path):
    p = _run(tmp_path, "FILE_TRANSFER")
    assert p.returncode == 0, p.stdout + p.stderr
    assert "MODE_OK=FILE_TRANSFER STATUS=FAIL" in p.stdout

def test_unknown_mode_fails_closed(tmp_path):
    p = _run(tmp_path, "SOMETHING_ELSE")
    assert p.returncode != 0
