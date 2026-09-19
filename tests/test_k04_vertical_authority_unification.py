from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from agp_cockpit.core.bridge_server import BridgeServerConfig, CockpitBridgeServer


def _post(server,path,body):
    port=server._server.server_address[1]
    req=Request(f"http://127.0.0.1:{port}{path}",data=body.encode(),method="POST",
                headers={"X-AGP-Token":"test-token","Content-Type":"application/json"})
    return urlopen(req,timeout=3)

@pytest.fixture
def server(tmp_path):
    s=CockpitBridgeServer(tmp_path,config=BridgeServerConfig(host="127.0.0.1",port=0,token="test-token"))
    s.start()
    try: yield s
    finally: s.stop()

def test_legacy_turn_authority_fails_closed(server):
    body=json.dumps({"conversation_url":"https://chatgpt.com/c/test","assistant_text":"{}","turn_id":"t"})
    with pytest.raises(HTTPError) as exc:
        _post(server,"/v1/turn",body)
    assert exc.value.code==410
    data=json.loads(exc.value.read())
    assert data["error"]=="LEGACY_TURN_AUTHORITY_RETIRED"
    assert data["next"]=="/v1/protocol/execute"

def test_source_keeps_authoritative_execute_path_and_disables_legacy_turn():
    s=Path("src/agp_cockpit/core/bridge_server.py").read_text()
    assert 'if path == "/v1/protocol/execute":' in s
    assert 'durable_controller_for(action.session_id)' in s
    active=s[s.index('if path == "/v1/turn":'):s.index('if path == "/v1/turn-legacy-disabled":')]
    assert "engine.handle_turn" not in active
    assert "LEGACY_TURN_AUTHORITY_RETIRED" in active
