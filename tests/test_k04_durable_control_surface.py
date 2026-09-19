from __future__ import annotations

import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_server import BridgeServerConfig, CockpitBridgeServer


def start(tmp_path):
 s=CockpitBridgeServer(tmp_path,config=BridgeServerConfig(host="127.0.0.1",port=0,token="t"),runtime_root=tmp_path/"rt"); s.start(); return s
def req(s,path,data=None):
 p=s._server.server_address[1]; body=None if data is None else json.dumps(data).encode()
 r=Request(f"http://127.0.0.1:{p}{path}",data=body,method="GET" if data is None else "POST",headers={"X-AGP-Token":"t","Content-Type":"application/json"})
 with urlopen(r,timeout=3) as x: return json.loads(x.read())
def test_done_is_only_completion_proposal(tmp_path):
 s=start(tmp_path)
 try:
  x=req(s,"/v1/task/complete-proposal",{"session_id":"s"}); assert x["accepted"]; assert x["task"]["state"]=="COMPLETE_PROPOSED"; assert x["task"]["state"]!="VERIFIED_COMPLETE"
  y=req(s,"/v1/task/status?session_id=s"); assert y["authority"]=="DurableTaskController"; assert y["task"]["state"]=="COMPLETE_PROPOSED"
 finally: s.stop()
def test_checkpoint_blocks_and_survives_restart(tmp_path):
 s=start(tmp_path)
 try:
  x=req(s,"/v1/task/checkpoint/request",{"session_id":"s","checkpoint_id":"cp","revision":"r","artifact_hash":"h"}); assert x["task"]["state"]=="SUSPENDED"; assert x["task"]["suspension_reason"]=="WAITING_FOR_HUMAN"
 finally: s.stop()
 s=start(tmp_path)
 try:
  x=req(s,"/v1/task/status?session_id=s"); assert x["task"]["suspension_reason"]=="WAITING_FOR_HUMAN"
  with pytest.raises(HTTPError) as e: req(s,"/v1/task/checkpoint/approve",{"session_id":"s","checkpoint_id":"cp","revision":"bad","artifact_hash":"h"})
  assert e.value.code==400
  assert req(s,"/v1/task/status?session_id=s")["task"]["suspension_reason"]=="WAITING_FOR_HUMAN"
  x=req(s,"/v1/task/checkpoint/approve",{"session_id":"s","checkpoint_id":"cp","revision":"r","artifact_hash":"h"}); assert x["task"]["state"]=="WAITING_FOR_REMOTE"; assert x["task"]["suspension_reason"] is None
 finally: s.stop()
def test_legacy_status_is_not_durable_task_status(tmp_path):
 s=start(tmp_path)
 try:
  d=req(s,"/v1/task/status?session_id=s"); l=req(s,"/v1/status"); assert d["authority"]=="DurableTaskController"; assert l.get("authority")!="DurableTaskController"
 finally: s.stop()
