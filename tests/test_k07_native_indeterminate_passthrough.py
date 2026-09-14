import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NATIVE = ROOT / "chrome_extension/browser_native_transport.js"

def _node(response):
    source = NATIVE.read_text()
    payload = json.dumps(response)
    js = """
const response = __RESPONSE__;
global.window = global;
global.location = {href:"https://chatgpt.com/", origin:"https://chatgpt.com", protocol:"https:", host:"chatgpt.com", hostname:"chatgpt.com", pathname:"/", search:"", hash:""};
global.document = {querySelectorAll: () => [{disabled:false, value:"", focus:()=>{}, getBoundingClientRect:()=>({width:100,height:20})}]};
global.HTMLTextAreaElement = function HTMLTextAreaElement() {};
global.crypto = {randomUUID: () => "req-test"};
global.chrome = {runtime:{lastError:null, sendMessage:(payload,callback)=>callback(Object.assign({},response,{request_id:payload.request_id}))}};
eval(__SOURCE__);
(async()=>{try{const value=await global.AGPBrowserNativeTransport.submit("probe"); console.log(JSON.stringify({resolved:true,value}));}catch(error){console.log(JSON.stringify({resolved:false,error:String(error)}));}})();
"""
    js = js.replace("__RESPONSE__", payload).replace("__SOURCE__", json.dumps(source))
    p = subprocess.run(["node","-e",js],cwd=ROOT,text=True,capture_output=True,check=True)
    return json.loads(p.stdout.strip().splitlines()[-1])

def test_indeterminate_response_is_passthrough_not_transport_exception():
    out=_node({"ok":False,"stage":"USER_TURN_INDETERMINATE","tab_id":1})
    assert out["resolved"] is True
    assert out["value"]["stage"] == "USER_TURN_INDETERMINATE"

def test_definitive_not_committed_response_still_rejects():
    out=_node({"ok":False,"stage":"USER_TURN_NOT_COMMITTED","tab_id":1})
    assert out["resolved"] is False
    assert "native transport rejected" in out["error"]

def test_other_false_response_still_rejects():
    out=_node({"ok":False,"stage":"OTHER_FAILURE","tab_id":1})
    assert out["resolved"] is False
    assert "native transport rejected" in out["error"]
