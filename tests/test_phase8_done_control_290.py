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
