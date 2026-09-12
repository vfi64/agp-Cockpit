(() => {
  "use strict";
  const C = window.AGPCockpitConversationContract;
  const P = window.AGPCockpitTransportProtocolV1;
  if (!C || !P) throw new Error("Phase7 dependencies missing");

  async function config() {
    const v = await chrome.storage.local.get({token:"", baseUrl:"http://127.0.0.1:8765"});
    if (!v.token) throw new Error("AGP bridge token missing");
    return {baseUrl:String(v.baseUrl).replace(/\/$/,""), token:String(v.token)};
  }
  async function runOneRound({protocolSnapshot = null, browserTimeoutMs = 120000} = {}) {
    // AGP_PHASE7_STABLE_PROTOCOL_ENTRY_326
    const snap = protocolSnapshot || await C.waitForCompletedProtocolAssistant({afterFingerprint:"", timeoutMs:browserTimeoutMs});
    const K = globalThis.AGPCockpitProtocolCanonicalizerV1;
    const canonicalText = K && typeof K.canonicalizeProtocolFrame === "function" ? K.canonicalizeProtocolFrame(snap.text) : snap.text;
    const action = P.parseAction(canonicalText);
    if (!["DIRECT_EXECUTION", "FILE_TRANSFER"].includes(action.mode)) throw new Error("Phase7 requires DIRECT_EXECUTION or FILE_TRANSFER");
    const cfg = await config();
    const r = await fetch(cfg.baseUrl + "/v1/protocol/execute", {
      method:"POST", headers:{"Content-Type":"text/plain","X-AGP-Token":cfg.token}, body:canonicalText
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "bridge execute failed");
    if (!["EXECUTED","REPLAYED"].includes(data.decision) || typeof data.result_frame !== "string") throw new Error("invalid bridge execution response");
    const result = P.parseResult(data.result_frame);
    if (result.action_id !== action.action_id || result.session_id !== action.session_id || result.round_id !== action.round_id)
      throw new Error("result correlation mismatch");
    await C.stageDraft(data.result_frame);
    const approval = await C.approveCurrentDraft();
    await C.sendApprovedDraft(approval);
    const ack = await fetch(cfg.baseUrl + "/v1/client-event", {
      method:"POST",
      headers:{"Content-Type":"application/json","X-AGP-Token":cfg.token},
      body:JSON.stringify({
        event:"RESULT_DELIVERED",
        details:{session_id:action.session_id,action_id:action.action_id}
      })
    });
    const ackData = await ack.json();
    if (!ack.ok || !["ACKNOWLEDGED","ALREADY_ACKNOWLEDGED"].includes(ackData.result_delivery))
      throw new Error(ackData.error || "durable result delivery acknowledgement failed");
    return {state:"DONE", session_id:action.session_id, round_id:action.round_id, action_id:action.action_id, assistant_fingerprint:snap.fingerprint, transport_status:result.transport_status};
  }
  window.AGPCockpitPhase7SingleRound = Object.freeze({runOneRound});
})();
