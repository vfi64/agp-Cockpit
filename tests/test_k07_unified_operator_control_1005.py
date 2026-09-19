from pathlib import Path

from agp_cockpit.core.operator_control import OperatorControlStore


def test_store_monotonic(tmp_path: Path):
 s=OperatorControlStore(tmp_path); assert s.current()=={"generation":0,"action":""}; assert s.request("PAUSE")=={"generation":1,"action":"PAUSE"}; assert s.request("RESUME")=={"generation":2,"action":"RESUME"}; assert s.request("STOP")=={"generation":3,"action":"STOP"}
def test_browser_contract():
 x=Path("chrome_extension/content.js").read_text(); assert "AGP_K07_UNIFIED_OPERATOR_CONTROL_1005" in x; assert 'api("/v1/file-loop/control")' in x; assert "await pollOperatorControl();" in x; assert "if (STATE.paused) return;" in x
def test_bridge_contract():
 x=Path("src/agp_cockpit/core/bridge_server.py").read_text(); assert x.count('path == "/v1/file-loop/control"')==2; assert "OperatorControlStore(runtime_root).current()" in x; assert "OperatorControlStore(runtime_root).request(action)" in x
