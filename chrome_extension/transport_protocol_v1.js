(() => {
"use strict";
const ACTION_BEGIN="AGP_COCKPIT_ACTION_BEGIN", ACTION_END="AGP_COCKPIT_ACTION_END";
const RESULT_BEGIN="AGP_COCKPIT_RESULT_BEGIN", RESULT_END="AGP_COCKPIT_RESULT_END";
const VERSION=1, MAX_BYTES=2000000;
const MODES=new Set(["DIRECT_EXECUTION","FILE_TRANSFER"]);
const STATUSES=new Set(["PASS","BLOCKED","FAIL","DONE","CANCELLED"]);
function fail(m){throw new Error("AGP protocol v1: "+m);}
function bytes(s){return new TextEncoder().encode(s).length;}
function frame(text,begin,end){
 if(typeof text!=="string"||bytes(text)>MAX_BYTES)fail("invalid/oversized frame");
 if(text.split(begin).length!==2||text.split(end).length!==2)fail("exactly one frame required");
 const a=text.indexOf(begin),b=text.indexOf(end);
 if(b<=a||text.slice(0,a).trim()||text.slice(b+end.length).trim())fail("malformed frame");
 const p=text.slice(a+begin.length,b).trim();
 if(!p||[ACTION_BEGIN,ACTION_END,RESULT_BEGIN,RESULT_END].some(m=>p.includes(m)))fail("empty/nested frame");
 let d;try{d=JSON.parse(p);}catch(_){fail("invalid JSON");}
 if(!d||Array.isArray(d)||typeof d!=="object")fail("payload must be object");return d;
}
function keys(d,e){if(JSON.stringify(Object.keys(d).sort())!==JSON.stringify([...e].sort()))fail("invalid fields");}
function id(d,k){if(typeof d[k]!=="string"||!d[k].trim())fail(k+" required");}
function version(d){if(d.protocol_version!==VERSION)fail("unsupported protocol_version");}
function parseAction(text){const d=frame(text,ACTION_BEGIN,ACTION_END);keys(d,["protocol_version","session_id","round_id","action_id","mode","target","work_order"]);version(d);id(d,"session_id");id(d,"round_id");id(d,"action_id");id(d,"target");if(!MODES.has(d.mode))fail("unsupported mode");return Object.freeze(d);}
function parseResult(text){const d=frame(text,RESULT_BEGIN,RESULT_END);keys(d,["protocol_version","session_id","round_id","action_id","status","result"]);version(d);id(d,"session_id");id(d,"round_id");id(d,"action_id");if(!STATUSES.has(d.status))fail("unsupported status");return Object.freeze(d);}
window.AGPCockpitTransportProtocolV1=Object.freeze({VERSION,ACTION_BEGIN,ACTION_END,RESULT_BEGIN,RESULT_END,parseAction,parseResult});
})();
