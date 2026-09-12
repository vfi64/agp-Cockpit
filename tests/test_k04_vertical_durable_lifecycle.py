from __future__ import annotations
import json,sqlite3
from urllib.request import Request,urlopen
from agp_cockpit.core.bridge_server import BridgeServerConfig,CockpitBridgeServer
from agp_cockpit.core.task_contract import LocalTaskContract
from agp_cockpit.core.transport_protocol_v1 import ActionEnvelope,encode_action_frame
def action(root,aid,argv):
 content=json.dumps({"kind":"generic","cwd":str(root),"argv":argv,"timeout_seconds":5,"label":aid})
 return ActionEnvelope(1,"vertical","round-"+aid,aid,"DIRECT_EXECUTION",{},{"type":"terminal_payload","content":content})
def post(s,a):
 p=s._server.server_address[1];req=Request(f"http://127.0.0.1:{p}/v1/protocol/execute",data=encode_action_frame(a).encode(),method="POST",headers={"X-AGP-Token":"t","Content-Type":"text/plain"})
 with urlopen(req,timeout=5) as r:return json.loads(r.read())
def server(root,rt):
 c=LocalTaskContract(root,allowed_effects=frozenset({"E2"}),allowed_tools=frozenset({"false","true"}),allow_network=False)
 return CockpitBridgeServer(root,config=BridgeServerConfig(host="127.0.0.1",port=0,token="t"),runtime_root=rt,local_task_contract=c)
def rows(db,aid):
 con=sqlite3.connect(db);con.row_factory=sqlite3.Row
 a=dict(con.execute("SELECT * FROM actions WHERE task_id=? AND action_id=?",("protocol-v1-http:vertical",aid)).fetchone())
 at=[dict(x) for x in con.execute("SELECT * FROM attempts WHERE task_id=? AND action_id=?",("protocol-v1-http:vertical",aid))]
 ev=[dict(x) for x in con.execute("SELECT * FROM evidence WHERE task_id=? AND action_id=?",("protocol-v1-http:vertical",aid))]
 con.close();return a,at,ev
def test_fail_is_durable_evidence_restart_duplicate_and_correction_continue(tmp_path):
 rt=tmp_path/"rt";s=server(tmp_path,rt);s.start()
 try:
  fail=post(s,action(tmp_path,"a1",["/usr/bin/false"]));assert fail["decision"]=="EXECUTED" and '"transport_status":"FAIL"' in fail["result_frame"]
 finally:s.stop()
 db=rt/"protocol-v1-actions.sqlite3";a,at,ev=rows(db,"a1")
 assert a["status"]=="FAIL" and a["attempt_count"]==1 and len(at)==1 and at[0]["status"]=="FAIL" and len(ev)==1 and ev[0]["outcome"]=="FAIL"
 s=server(tmp_path,rt);s.start()
 try:
  dup=post(s,action(tmp_path,"a1",["/usr/bin/false"]));assert dup["decision"]=="DUPLICATE" and dup["replayed"] is False
  p=s._server.server_address[1]
  req=Request(f"http://127.0.0.1:{p}/v1/client-event",data=json.dumps({"event":"RESULT_DELIVERED","details":{"session_id":"vertical","action_id":"a1"}}).encode(),method="POST",headers={"X-AGP-Token":"t","Content-Type":"application/json"})
  with urlopen(req,timeout=5) as r:
   ack=json.loads(r.read())
  assert ack["result_delivery"]=="ACKNOWLEDGED"
  ok=post(s,action(tmp_path,"a2",["/usr/bin/true"]));assert ok["decision"]=="EXECUTED" and '"transport_status":"PASS"' in ok["result_frame"]
 finally:s.stop()
 a,at,ev=rows(db,"a2");assert a["status"]=="PASS" and a["attempt_count"]==1 and len(at)==1 and at[0]["status"]=="PASS" and len(ev)==1 and ev[0]["outcome"]=="PASS"
