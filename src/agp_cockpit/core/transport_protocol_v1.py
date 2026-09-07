from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from typing import Any, Literal
PROTOCOL_VERSION=1
MAX_FRAME_BYTES=2_000_000
ACTION_BEGIN="AGP_COCKPIT_ACTION_BEGIN"
ACTION_END="AGP_COCKPIT_ACTION_END"
RESULT_BEGIN="AGP_COCKPIT_RESULT_BEGIN"
RESULT_END="AGP_COCKPIT_RESULT_END"
CONTROL_BEGIN="AGP_COCKPIT_CONTROL_BEGIN"
CONTROL_END="AGP_COCKPIT_CONTROL_END"
VALID_MODES=frozenset({"DIRECT_EXECUTION","FILE_TRANSFER"})
VALID_STATUSES=frozenset({"PASS","BLOCKED","FAIL","DONE","CANCELLED"})
VALID_CONTROLS=frozenset({"DONE"})
class ProtocolViolation(ValueError): pass
@dataclass(frozen=True)
class ActionEnvelope:
    protocol_version:int; session_id:str; round_id:str; action_id:str
    mode:Literal["DIRECT_EXECUTION","FILE_TRANSFER"]; target:dict[str,Any]; work_order:Any
@dataclass(frozen=True)
class ResultEnvelope:
    protocol_version:int; session_id:str; round_id:str; action_id:str
    transport_status:Literal["PASS","BLOCKED","FAIL","DONE","CANCELLED"]; local_execution:Any
@dataclass(frozen=True)
class ActionRegistration:
    decision:Literal["DISPATCH","DUPLICATE"]; action:ActionEnvelope
def _json_bytes(data):
    return json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
def _id(data,key):
    v=data.get(key)
    if not isinstance(v,str) or not v.strip(): raise ProtocolViolation(f"{key} must be a non-empty string")
    return v
def _keys(data,expected):
    if set(data)!=expected:
        raise ProtocolViolation(f"invalid fields: missing={sorted(expected-set(data))}, extra={sorted(set(data)-expected)}")
def _version(data):
    v=data.get("protocol_version")
    if type(v) is not int or v!=PROTOCOL_VERSION: raise ProtocolViolation(f"unsupported protocol_version: {v!r}")
    return v
def _object(raw):
    if not isinstance(raw,str): raise ProtocolViolation("frame payload must be text")
    if len(raw.encode())>MAX_FRAME_BYTES: raise ProtocolViolation("frame exceeds maximum size")
    try: data=json.loads(raw)
    except json.JSONDecodeError as exc: raise ProtocolViolation(f"invalid JSON: {exc.msg}") from exc
    if not isinstance(data,dict): raise ProtocolViolation("payload must be a JSON object")
    return data
def _frame(text,begin,end):
    if not isinstance(text,str): raise ProtocolViolation("frame must be text")
    if len(text.encode())>MAX_FRAME_BYTES: raise ProtocolViolation("frame exceeds maximum size")
    if text.count(begin)!=1 or text.count(end)!=1: raise ProtocolViolation("frame must contain exactly one begin/end marker")
    a=text.find(begin); b=text.find(end)
    if b<=a: raise ProtocolViolation("truncated, nested, or reversed frame")
    if text[:a].strip() or text[b+len(end):].strip(): raise ProtocolViolation("prose outside frame is not allowed")
    payload=text[a+len(begin):b].strip()
    if not payload: raise ProtocolViolation("empty frame payload")
    if any(m in payload for m in (ACTION_BEGIN,ACTION_END,RESULT_BEGIN,RESULT_END)): raise ProtocolViolation("nested protocol marker")
    return payload
def parse_action_frame(text):
    d=_object(_frame(text,ACTION_BEGIN,ACTION_END))
    _keys(d,{"protocol_version","session_id","round_id","action_id","mode","target","work_order"})
    v=_version(d); s=_id(d,"session_id"); r=_id(d,"round_id"); a=_id(d,"action_id")
    if d["mode"] not in VALID_MODES: raise ProtocolViolation(f"unsupported mode: {d['mode']!r}")
    t=d["target"]
    if not isinstance(t,dict): raise ProtocolViolation("target must be object")
    return ActionEnvelope(v,s,r,a,d["mode"],t,d["work_order"])
def parse_result_frame(text):
    d=_object(_frame(text,RESULT_BEGIN,RESULT_END))
    _keys(d,{"protocol_version","session_id","round_id","action_id","transport_status","local_execution"})
    v=_version(d); s=_id(d,"session_id"); r=_id(d,"round_id"); a=_id(d,"action_id")
    if d["transport_status"] not in VALID_STATUSES: raise ProtocolViolation(f"unsupported transport_status: {d['transport_status']!r}")
    return ResultEnvelope(v,s,r,a,d["transport_status"],d["local_execution"])
def encode_action_frame(a):
    d={"protocol_version":a.protocol_version,"session_id":a.session_id,"round_id":a.round_id,"action_id":a.action_id,"mode":a.mode,"target":a.target,"work_order":a.work_order}
    p=_json_bytes(d).decode(); f=f"{ACTION_BEGIN}\n{p}\n{ACTION_END}"; parse_action_frame(f); return f
def encode_result_frame(r):
    d={"protocol_version":r.protocol_version,"session_id":r.session_id,"round_id":r.round_id,"action_id":r.action_id,"transport_status":r.transport_status,"local_execution":r.local_execution}
    p=_json_bytes(d).decode(); f=f"{RESULT_BEGIN}\n{p}\n{RESULT_END}"; parse_result_frame(f); return f
def action_digest(a):
    return hashlib.sha256(_json_bytes({"protocol_version":a.protocol_version,"session_id":a.session_id,"round_id":a.round_id,"action_id":a.action_id,"mode":a.mode,"target":a.target,"work_order":a.work_order})).hexdigest()
class ActionRegistry:
    def __init__(self): self._seen={}; self._ambiguous=set()
    def register(self,a):
        digest=action_digest(a); old=self._seen.get(a.action_id)
        if a.action_id in self._ambiguous: raise ProtocolViolation("action_id has ambiguous prior execution; automatic replay forbidden")
        if old is None: self._seen[a.action_id]=digest; return ActionRegistration("DISPATCH",a)
        if old!=digest: raise ProtocolViolation("action_id reused with changed payload")
        return ActionRegistration("DUPLICATE",a)
    def mark_ambiguous(self,action_id):
        if not isinstance(action_id,str) or not action_id.strip(): raise ProtocolViolation("action_id must be a non-empty string")
        self._ambiguous.add(action_id)

@dataclass(frozen=True)
class ControlEnvelope:
    protocol_version:int; session_id:str; round_id:str; control:Literal["DONE"]

def parse_control_frame(text):
    d=_object(_frame(text,CONTROL_BEGIN,CONTROL_END))
    _keys(d,{"protocol_version","session_id","round_id","control"})
    v=_version(d); s=_id(d,"session_id"); r=_id(d,"round_id")
    if d["control"] not in VALID_CONTROLS: raise ProtocolViolation(f"unsupported control: {d[chr(39)+chr(99)+chr(111)+chr(110)+chr(116)+chr(114)+chr(111)+chr(108)+chr(39)]!r}")
    return ControlEnvelope(v,s,r,d["control"])

def encode_control_frame(c):
    d={"protocol_version":c.protocol_version,"session_id":c.session_id,"round_id":c.round_id,"control":c.control}
    p=_json_bytes(d).decode(); f=f"{CONTROL_BEGIN}\n{p}\n{CONTROL_END}"; parse_control_frame(f); return f
