from __future__ import annotations
import json,subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[1];J=R/'chrome_extension/protocol_canonicalizer_v1.js'
def call(t):
 c='global.window=global;require('+json.dumps(str(J))+');try{const x=AGPCockpitProtocolCanonicalizerV1.canonicalizeProtocolFrame('+json.dumps(t)+');console.log(JSON.stringify({ok:true,text:x}))}catch(e){console.log(JSON.stringify({ok:false,error:String(e)}))}';p=subprocess.run(['node','-e',c],cwd=R,text=True,capture_output=True);assert p.returncode==0,p.stderr;return json.loads(p.stdout)
def frame(o):return 'AGP_COCKPIT_ACTION_BEGIN\n'+json.dumps(o,separators=(',',':'))+'\nAGP_COCKPIT_ACTION_END'
def base(w):return {'protocol_version':1,'session_id':'s','round_id':'r','action_id':'a','mode':'FILE_TRANSFER','target':{'repository_path_hint':'/repo'},'work_order':w}
def payload(t):return json.loads(t.split('AGP_COCKPIT_ACTION_BEGIN',1)[1].split('AGP_COCKPIT_ACTION_END',1)[0].strip())
def test_prose_fence():assert call('prose\n```json\n'+frame(base({'type':'terminal_payload','content':'{}'}))+'\n```')['ok']
def test_content_object():assert isinstance(payload(call(frame(base({'type':'terminal_payload','content':{'kind':'kit','cwd':'/repo','argv':['kit','x']}})))['text'])['work_order']['content'],str)
def test_structured_work_order():
 w={'kind':'generic','cwd':'/repo','argv':['kit','transfer','remote-next','--json'],'label':'x'};assert json.loads(payload(call(frame(base(w)))['text'])['work_order']['content'])==w
def test_lost_escaping():
 i='{"kind":"kit","cwd":"/repo","argv":["kit","x"]}';g=frame(base({'type':'terminal_payload','content':i}));assert call(g.replace(json.dumps(i),'"'+i+'"'))['ok']
def test_ambiguous_fails():
 f=frame(base({'type':'terminal_payload','content':'{}'}));d=call(f+'\n'+f);assert not d['ok'] and 'AMBIGUOUS' in d['error']
def test_semantics_preserved():
 o=base({'type':'terminal_payload','content':'{}'});o['mode']='FILE-TRANSFER';assert payload(call(frame(o))['text'])['mode']=='FILE-TRANSFER'

