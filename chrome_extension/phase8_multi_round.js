(() => {
"use strict";
const P7=window.AGPCockpitPhase7SingleRound;if(!P7)throw new Error("Phase8 dependency missing");
const sleep=ms=>new Promise(r=>setTimeout(r,ms));let running=false,paused=false,stopRequested=false;
function pause(){paused=true;} function resume(){paused=false;} function stop(){stopRequested=true;}
async function run({maxRounds=3,pausePollMs=50,browserTimeoutMs=120000,onRoundCompleted=null}={}){
 // AGP_PHASE8_BROWSER_WAIT_TIMEOUT_300

 if(running)throw new Error("PHASE8_ALREADY_RUNNING");
 if(!Number.isInteger(maxRounds)||maxRounds<1||maxRounds>100)throw new Error("PHASE8_INVALID_MAX_ROUNDS");
 if(!Number.isInteger(browserTimeoutMs)||browserTimeoutMs<1000||browserTimeoutMs>600000)throw new Error("PHASE8_INVALID_BROWSER_TIMEOUT");
 running=true;stopRequested=false;let completed=0,last=null;
 const C=window.AGPCockpitConversationContract,T=window.AGPCockpitTransportProtocolV1;
 if(!C||!T||typeof C.waitForCompletedProtocolAssistant!=="function"||typeof T.parseControl!=="function")throw new Error("PHASE8_PROTOCOL_DEPENDENCY_MISSING");
 let pending=await C.waitForCompletedProtocolAssistant({afterFingerprint:"",timeoutMs:browserTimeoutMs});
 try{while(completed<maxRounds){
  while(paused&&!stopRequested)await sleep(pausePollMs);if(stopRequested)return {state:"USER_STOPPED",rounds:completed,last};
  // AGP_PHASE8_PROTOCOL_STATE_MACHINE_326
  try{const ctl=T.parseControl(pending.text);if(ctl.control==="DONE"){if(last&&last.session_id&&ctl.session_id!==last.session_id)throw new Error("PHASE8_DONE_SESSION_MISMATCH");return {state:"DONE",rounds:completed,last,control:ctl};}}
  catch(e){if(String(e&&e.message||e).includes("PHASE8_DONE_SESSION_MISMATCH"))throw e;}
  last=await P7.runOneRound({protocolSnapshot:pending,browserTimeoutMs});completed++;
  // AGP_PHASE8_LIVE_ROUND_PROGRESS_328
  if(typeof onRoundCompleted==="function"){try{onRoundCompleted(Object.freeze({rounds:completed,last}));}catch(_){}}
  if(!last||last.state!=="DONE")return {state:(last&&last.state)||"FAIL",rounds:completed,last};
  if(["BLOCKED","FAIL","CANCELLED"].includes(last.transport_status))return {state:last.transport_status,rounds:completed,last};
  if(stopRequested)return {state:"USER_STOPPED",rounds:completed,last};
  if(completed>=maxRounds)return {state:"MAX_ROUNDS_REACHED",rounds:completed,last};
  pending=await C.waitForCompletedProtocolAssistant({afterFingerprint:last.assistant_fingerprint,timeoutMs:browserTimeoutMs});
 }
 return {state:"MAX_ROUNDS_REACHED",rounds:completed,last};
 }finally{running=false;paused=false;stopRequested=false;}
}
window.AGPCockpitPhase8MultiRound=Object.freeze({run,pause,resume,stop});
})();
