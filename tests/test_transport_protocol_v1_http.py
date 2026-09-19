from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_server import BridgeServerConfig, CockpitBridgeServer
from agp_cockpit.core.transport_protocol_v1 import ActionEnvelope, encode_action_frame


def post(server, body):
    url=f"http://127.0.0.1:{server._server.server_address[1]}/v1/protocol/action"
    req=Request(url,data=body.encode(),method="POST",headers={"X-AGP-Token":"test-token","Content-Type":"text/plain"})
    with urlopen(req,timeout=3) as r: return r.status,json.loads(r.read())

@pytest.fixture
def server(tmp_path):
    s=CockpitBridgeServer(tmp_path,config=BridgeServerConfig(host="127.0.0.1",port=0,token="test-token"))
    s.start()
    try: yield s
    finally: s.stop()

def frame(**kw):
    d={"protocol_version": 1,"session_id": "s","round_id": "r","action_id": "a","mode": "DIRECT_EXECUTION","target": {"repository_path_hint":"/repo"},"work_order": {"opaque":True}}
    d.update(kw); return encode_action_frame(ActionEnvelope(**d))

def test_http_boundary_accepts_first_action_without_interpreting_payload(server):
    status,data=post(server,frame(work_order={"arbitrary":{"kit":"opaque"}}))
    assert status==200 and data["decision"]=="DISPATCH" and data["action_id"]=="a"

def test_http_boundary_identical_duplicate_is_not_redispatched(server):
    body=frame()
    assert post(server,body)[1]["decision"]=="DISPATCH"
    assert post(server,body)[1]["decision"]=="DUPLICATE"

def test_http_boundary_changed_payload_same_action_id_fails_closed(server):
    post(server,frame())
    with pytest.raises(HTTPError) as exc: post(server,frame(work_order={"changed":1}))
    assert exc.value.code==400

def test_http_boundary_malformed_protocol_fails_closed(server):
    with pytest.raises(HTTPError) as exc: post(server,"AGP_COCKPIT_ACTION_BEGIN\n{}\nAGP_COCKPIT_ACTION_END")
    assert exc.value.code==400

def test_legacy_turn_endpoint_remains_present():
    assert 'path == "/v1/turn"' in Path("src/agp_cockpit/core/bridge_server.py").read_text()
