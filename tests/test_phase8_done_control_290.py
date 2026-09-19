import json
from pathlib import Path

import pytest

from agp_cockpit.core.transport_protocol_v1 import (
 ControlEnvelope,
 ProtocolViolation,
 encode_control_frame,
 parse_control_frame,
)

ROOT=Path(__file__).resolve().parents[1]
def test_done_control_roundtrip():
 c=ControlEnvelope(1,"s1","round-done","DONE");assert parse_control_frame(encode_control_frame(c))==c
def test_control_is_strict_and_not_a_third_communication_mode():
 f=encode_control_frame(ControlEnvelope(1,"s1","rd","DONE"));d=json.loads(f.splitlines()[1]);d["mode"]="DIRECT_EXECUTION"
 with pytest.raises(ProtocolViolation):parse_control_frame("AGP_COCKPIT_CONTROL_BEGIN\n"+json.dumps(d)+"\nAGP_COCKPIT_CONTROL_END")
 py=(ROOT/"src/agp_cockpit/core/transport_protocol_v1.py").read_text();assert 'VALID_MODES=frozenset({"DIRECT_EXECUTION","FILE_TRANSFER"})' in py
def test_browser_protocol_has_explicit_done_control():
 t=(ROOT/"chrome_extension/transport_protocol_v1.js").read_text()
 for x in ("AGP_COCKPIT_CONTROL_BEGIN","AGP_COCKPIT_CONTROL_END","parseControl","CONTROLS=new Set([\"DONE\"])"):assert x in t
def test_phase7_returns_fingerprint_and_session_for_phase8_freshness():
 t=(ROOT/"chrome_extension/phase7_single_round.js").read_text();assert "assistant_fingerprint:snap.fingerprint" in t and "session_id:action.session_id" in t
def test_phase8_waits_for_fresh_assistant_before_next_round():
 t=(ROOT/"chrome_extension/phase8_multi_round.js").read_text();assert "waitForCompletedProtocolAssistant({afterFingerprint:last.assistant_fingerprint,timeoutMs:browserTimeoutMs})" in t and "parseControl" in t
def test_phase8_done_is_not_derived_from_local_result_status():
 t=(ROOT/"chrome_extension/phase8_multi_round.js").read_text();assert 'last.transport_status==="DONE"' not in t
