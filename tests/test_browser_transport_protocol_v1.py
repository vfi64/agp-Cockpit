import json
from pathlib import Path


def test_protocol_v1_loaded_before_conversation_contract():
    m=json.loads(Path("chrome_extension/manifest.json").read_text()); js=m["content_scripts"][0]["js"]
    assert "transport_protocol_v1.js" in js
    assert js.index("transport_protocol_v1.js") < js.index("conversation_contract.js")
def test_browser_protocol_has_canonical_markers_and_fields():
    t=Path("chrome_extension/transport_protocol_v1.js").read_text()
    for token in ["AGP_COCKPIT_ACTION_BEGIN","AGP_COCKPIT_ACTION_END","AGP_COCKPIT_RESULT_BEGIN","AGP_COCKPIT_RESULT_END","protocol_version","session_id","round_id","action_id","DIRECT_EXECUTION","FILE_TRANSFER","target","work_order"]:
        assert token in t
def test_browser_protocol_is_transport_only():
    t=Path("chrome_extension/transport_protocol_v1.js").read_text().lower()
    for forbidden in ["agentic-kit","git ","github","mission_bootstrap","work finish","file_transfer/"]:
        assert forbidden not in t
def test_browser_protocol_fails_closed_structurally():
    t=Path("chrome_extension/transport_protocol_v1.js").read_text()
    for token in ["exactly one frame required","empty/nested frame","unsupported protocol_version","invalid fields","unsupported mode"]:
        assert token in t
